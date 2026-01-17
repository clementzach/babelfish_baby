"""
OpenAI chatbot integration for cry-specific advice.
"""
import os
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from openai import OpenAI

from app.models import CryInstance, ChatConversation
from app.utils.photo import get_photo_base64, get_photo_mimetype

logger = logging.getLogger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def generate_advice(
    cry_id: int,
    user_message: str,
    db: Session,
) -> str:
    """
    Generate contextual advice using OpenAI.

    Args:
        cry_id: Cry instance ID for context
        user_message: Latest user message
        db: Database session

    Returns:
        Bot response text

    Raises:
        Exception: If generation fails
    """
    if not client:
        raise ValueError("OpenAI client not initialized (API key missing)")

    # Get cry instance
    cry = db.query(CryInstance).filter(CryInstance.id == cry_id).first()
    if not cry:
        raise ValueError(f"Cry not found: {cry_id}")

    # Get chat history
    chat_history = (
        db.query(ChatConversation)
        .filter(ChatConversation.cry_instance_id == cry_id)
        .order_by(ChatConversation.timestamp)
        .all()
    )

    # Build context with free-text reason and solution
    reason_text = cry.reason if cry.reason else "not yet determined"
    solution_text = cry.solution if cry.solution else "not yet recorded"

    # Check if photo is available
    has_photo = cry.photo_file_path and os.path.exists(cry.photo_file_path)
    photo_note = "\n- A photo of the baby has been provided. Please reference the baby's visual state (facial expressions, body language, surroundings) in your analysis." if has_photo else ""

    context = f"""You are advising a parent about a baby crying episode.

Context:
- Cry reason: {reason_text}
- Solution that helped: {solution_text}
- Time recorded: {cry.recorded_at.strftime("%B %d, %Y at %I:%M %p")}
- Parent's notes: {cry.notes if cry.notes else "None"}{photo_note}

Provide practical, safe, evidence-based advice. Keep responses concise (3-4 sentences).
Always prioritize safety and suggest consulting a pediatrician for concerning symptoms.
When the parent asks for help identifying the reason or solution, you can suggest updating
the cry record with your insights based on the conversation.
"""

    # Build messages for OpenAI
    if has_photo:
        # Include photo in the first user message
        photo_base64 = get_photo_base64(cry.photo_file_path)
        photo_mimetype = get_photo_mimetype(cry.photo_file_path)

        messages = [
            {"role": "system", "content": context},
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
                        "text": "This is a photo of the baby during or shortly after the crying episode."
                    }
                ]
            },
            {
                "role": "assistant",
                "content": "I can see the photo. I'll reference the baby's visual state in my advice."
            }
        ]
    else:
        messages = [{"role": "system", "content": context}]

    # Add chat history
    for msg in chat_history:
        messages.append({
            "role": "user" if msg.sender == "user" else "assistant",
            "content": msg.message_text,
        })

    # Add current message
    messages.append({"role": "user", "content": user_message})

    try:
        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )

        bot_response = response.choices[0].message.content.strip()
        logger.info(f"Generated advice for cry_id={cry_id}")

        return bot_response

    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        raise Exception(f"Failed to generate advice: {str(e)}")
