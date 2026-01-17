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
from app.vector_db import search_similar, update_embedding_metadata
from app.ai.embedding_standardization import process_and_store_embedding
from app.utils.photo import get_photo_base64, get_photo_mimetype

logger = logging.getLogger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
NUM_SIMILAR_CRIES = 3
NUM_CRIES_FOR_PREDICTIONS = 5


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

        # Generate embedding (do this for ALL cries, not just after NUM_CRIES_FOR_PREDICTIONS validations)
        logger.info(f"Generating embedding for cry_id={cry_id}")
        try:
            embedding = generate_embedding(cry.audio_file_path)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate embedding: {str(e)}",
            }

        # Process and store embedding (raw + standardized)
        logger.info(f"Processing and storing embedding for cry_id={cry_id}")
        try:
            process_and_store_embedding(
                db=db,
                cry_id=cry_id,
                user_id=user_id,
                raw_embedding=embedding,
                reason=cry.reason,
                timestamp=cry.recorded_at.isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to process and store embedding: {e}")
            # Continue anyway, we can still try to search

        # Need at least NUM_CRIES_FOR_PREDICTIONS validated recordings for predictions
        if validated_count < NUM_CRIES_FOR_PREDICTIONS:
            logger.info(f"Not enough validated data for user {user_id}, skipping AI prediction")
            return {
                "status": "needs_manual_labeling",
                "message": "Please label more recordings before AI predictions can begin",
                "validated_count": validated_count,
            }

        # Search for similar cries
        logger.info(f"Searching for similar cries for user_id={user_id}")
        similar_cries = search_similar(
            user_id=user_id,
            embedding=embedding,
            k=NUM_SIMILAR_CRIES,
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
        prediction = await call_openai_for_prediction(historical_data, cry)

        if not prediction:
            return {
                "status": "prediction_failed",
                "message": "Failed to generate prediction",
            }

        # Update cry instance with AI prediction (user will validate later)
        cry.ai_reason = prediction["reason"]
        cry.ai_solution = prediction["solution"]
        if "notes" in prediction and not cry.notes:
            cry.notes = prediction["notes"]
        db.commit()

        logger.info(f"Prediction complete for cry_id={cry_id}: {prediction['reason']}")

        return {
            "status": "success",
            "reason": prediction["reason"],
            "solution": prediction["solution"],
            "notes": prediction.get("notes", ""),
            "confidence": "normal" if validated_count >= NUM_CRIES_FOR_PREDICTIONS else "low",
        }

    except Exception as e:
        logger.error(f"Prediction pipeline failed for cry_id={cry_id}: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def call_openai_for_prediction(historical_data: list, cry: CryInstance) -> Optional[dict]:
    """
    Call OpenAI to predict cry reason and solution based on historical data.

    Args:
        historical_data: List of similar past cries with reasons, solutions, and notes
        cry: Current CryInstance (for photo if available)

    Returns:
        Prediction dict with reason, solution, and notes
    """
    if not client:
        logger.error("OpenAI client not initialized (API key missing)")
        return None

    try:
        # Check if photo is available for this cry
        has_photo = cry.photo_file_path and os.path.exists(cry.photo_file_path)
        photo_note = "\n\nA photo of the baby has been provided. Please reference the baby's visual state (facial expressions, body language, surroundings) in your analysis." if has_photo else ""

        # Build prompt
        system_prompt = f"""You are an expert baby cry analyzer. Based on similar past recordings,
predict why the baby is crying now and suggest a solution that might help.

Provide:
1. A brief reason (2-5 words, e.g., "hungry", "tired", "needs diaper change")
2. A practical solution (1 sentence, e.g., "Try feeding", "Rock gently to sleep")
3. Optional brief notes if relevant (1 sentence)

Respond in JSON format with keys: "reason", "solution", "notes"{photo_note}
"""

        user_prompt_text = f"""Similar past cries:

"""
        for i, data in enumerate(historical_data, 1):
            user_prompt_text += f"{i}. Reason: {data['reason']}, Solution: {data['solution']}, Notes: {data['notes']}, Similarity: {data['similarity']}\n"

        user_prompt_text += "\nBased on these similar past recordings, predict the most likely reason and suggest a solution."

        logger.info(f"Calling model with user prompt: " + user_prompt_text)

        # Build messages based on whether photo is available
        if has_photo:
            # Include photo in the user message
            photo_base64 = get_photo_base64(cry.photo_file_path)
            photo_mimetype = get_photo_mimetype(cry.photo_file_path)

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{photo_mimetype};base64,{photo_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt_text
                        }
                    ]
                }
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_text},
            ]

        # Call OpenAI (using gpt-4.1-mini for cost efficiency and better performance)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )

        # Parse JSON response
        content = response.choices[0].message.content.strip()

        # Handle potential markdown code blocks in response
        if content.startswith("```"):
            # Extract JSON from markdown code block
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        prediction_data = json.loads(content)

        return {
            "reason": prediction_data.get("reason", "Unknown"),
            "solution": prediction_data.get("solution", ""),
        }

    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return None
