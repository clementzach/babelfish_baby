"""
OpenAI chatbot integration for cry-specific advice.
"""
import os
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from openai import OpenAI

from app.models import CryInstance, CryCategory, ChatConversation

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

    # Get category name
    category_name = "unknown"
    if cry.category_id:
        category = db.query(CryCategory).filter(CryCategory.id == cry.category_id).first()
        if category:
            category_name = category.name

    # Get chat history
    chat_history = (
        db.query(ChatConversation)
        .filter(ChatConversation.cry_instance_id == cry_id)
        .order_by(ChatConversation.timestamp)
        .all()
    )

    # Build context
    context = f"""You are advising a parent about a baby crying episode.

Context:
- Cry reason: {category_name}
- Time recorded: {cry.recorded_at.strftime("%B %d, %Y at %I:%M %p")}
- Parent's notes: {cry.notes if cry.notes else "None"}

Provide practical, safe, evidence-based advice. Keep responses concise (3-4 sentences).
Always prioritize safety and suggest consulting a pediatrician for concerning symptoms.
"""

    # Build messages for OpenAI
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
