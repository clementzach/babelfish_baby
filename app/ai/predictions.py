"""
AI prediction pipeline for cry analysis.
"""
import os
import logging
from typing import Optional
from sqlalchemy.orm import Session
from openai import OpenAI
import json

from app.models import CryInstance
from app.ai.embeddings import generate_embedding
from app.vector_db import add_embedding, search_similar, update_embedding_metadata

logger = logging.getLogger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def predict_cry_reason(cry_id: int, user_id: int, db: Session) -> Optional[dict]:
    """
    Full prediction pipeline for a cry recording.

    Steps:
    1. Check if user has enough validated data
    2. Generate embedding using MERT
    3. Store embedding in Chroma
    4. Find similar cries (KNN search)
    5. Retrieve historical reasons and solutions
    6. Call OpenAI to predict reason and solution
    7. Update database

    Args:
        cry_id: Cry instance ID
        user_id: User ID
        db: Database session

    Returns:
        Prediction result dict or None if prediction not possible
    """
    try:
        # Get cry instance
        cry = db.query(CryInstance).filter(CryInstance.id == cry_id).first()
        if not cry:
            logger.error(f"Cry not found: cry_id={cry_id}")
            return None

        # Check user's validated cry count
        validated_count = (
            db.query(CryInstance)
            .filter(
                CryInstance.user_id == user_id,
                CryInstance.validation_status == True,
                CryInstance.reason.isnot(None),
            )
            .count()
        )

        logger.info(f"User {user_id} has {validated_count} validated recordings")

        # Need at least 3 validated recordings for predictions
        if validated_count < 3:
            logger.info(f"Not enough validated data for user {user_id}, skipping AI prediction")
            return {
                "status": "needs_manual_labeling",
                "message": "Please label more recordings before AI predictions can begin",
                "validated_count": validated_count,
            }

        # Generate embedding
        logger.info(f"Generating embedding for cry_id={cry_id}")
        try:
            embedding = generate_embedding(cry.audio_file_path)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate embedding: {str(e)}",
            }

        # Store embedding in Chroma
        logger.info(f"Storing embedding in Chroma for cry_id={cry_id}")
        try:
            add_embedding(
                cry_id=cry_id,
                user_id=user_id,
                embedding=embedding,
                reason=cry.reason,
                timestamp=cry.recorded_at.isoformat(),
            )
        except Exception as e:
            logger.error(f"Failed to store embedding in Chroma: {e}")
            # Continue anyway, we can still try to search

        # Search for similar cries
        logger.info(f"Searching for similar cries for user_id={user_id}")
        similar_cries = search_similar(
            user_id=user_id,
            embedding=embedding,
            k=5,
            filter_validated=True,
        )

        if not similar_cries or len(similar_cries) == 0:
            logger.info(f"No similar cries found for user {user_id}")
            return {
                "status": "no_similar_cries",
                "message": "No similar cries found in your history",
            }

        # Get reason and solution for similar cries
        historical_data = []
        for similar in similar_cries:
            similar_cry_id = similar["cry_id"]
            similar_cry = db.query(CryInstance).filter(CryInstance.id == similar_cry_id).first()

            if similar_cry and similar_cry.reason:
                historical_data.append(
                    {
                        "reason": similar_cry.reason,
                        "solution": similar_cry.solution or "Not recorded",
                        "notes": similar_cry.notes or "",
                        "similarity": f"{similar['similarity']:.2f}",
                    }
                )

        if not historical_data:
            logger.info(f"No historical data available for user {user_id}")
            return {
                "status": "no_historical_data",
                "message": "Could not retrieve historical data",
            }

        # Call OpenAI to predict reason and solution
        logger.info(f"Calling OpenAI to predict reason and solution for cry_id={cry_id}")
        prediction = await call_openai_for_prediction(historical_data)

        if not prediction:
            return {
                "status": "prediction_failed",
                "message": "Failed to generate prediction",
            }

        # Update cry instance with prediction
        cry.reason = prediction["reason"]
        cry.reason_source = "ai"
        cry.solution = prediction["solution"]
        cry.solution_source = "ai"
        if "notes" in prediction:
            cry.notes = prediction["notes"]
        db.commit()

        logger.info(f"Prediction complete for cry_id={cry_id}: {prediction['reason']}")

        return {
            "status": "success",
            "reason": prediction["reason"],
            "solution": prediction["solution"],
            "notes": prediction.get("notes", ""),
            "confidence": "normal" if validated_count >= 5 else "low",
        }

    except Exception as e:
        logger.error(f"Prediction pipeline failed for cry_id={cry_id}: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def call_openai_for_prediction(historical_data: list) -> Optional[dict]:
    """
    Call OpenAI to predict cry reason and solution based on historical data.

    Args:
        historical_data: List of similar past cries with reasons, solutions, and notes

    Returns:
        Prediction dict with reason, solution, and notes
    """
    if not client:
        logger.error("OpenAI client not initialized (API key missing)")
        return None

    try:
        # Build prompt
        system_prompt = """You are an expert baby cry analyzer. Based on similar past recordings,
predict why the baby is crying now and suggest a solution that might help.

Provide:
1. A brief reason (2-5 words, e.g., "hungry", "tired", "needs diaper change")
2. A practical solution (1 sentence, e.g., "Try feeding", "Rock gently to sleep")
3. Optional brief notes if relevant (1 sentence)

Respond in JSON format with keys: "reason", "solution", "notes"
"""

        user_prompt = f"""Similar past cries:

"""
        for i, data in enumerate(historical_data, 1):
            user_prompt += f"{i}. Reason: {data['reason']}, Solution: {data['solution']}, Notes: {data['notes']}, Similarity: {data['similarity']}\n"

        user_prompt += "\nBased on these similar past recordings, predict the most likely reason and suggest a solution."

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        # Parse JSON response
        content = response.choices[0].message.content.strip()
        prediction_data = json.loads(content)

        return {
            "reason": prediction_data.get("reason", "Unknown"),
            "solution": prediction_data.get("solution", ""),
            "notes": prediction_data.get("notes", ""),
        }

    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return None
