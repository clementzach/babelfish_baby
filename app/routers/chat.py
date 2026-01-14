"""
Chat endpoints for cry-specific advice.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, CryInstance, ChatConversation
from app.ai.chatbot import generate_advice

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Request models
class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


# Response models
class ChatMessageResponse(BaseModel):
    bot_response: str
    timestamp: str


class ChatHistoryItem(BaseModel):
    message_id: int
    sender: str
    message_text: str
    timestamp: str

    class Config:
        from_attributes = True


@router.post("/{cry_id}/message", response_model=ChatMessageResponse)
async def send_chat_message(
    cry_id: int,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a chat message and get AI advice.

    Args:
        cry_id: Cry instance ID
        request: Message data
        current_user: Authenticated user
        db: Database session

    Returns:
        Bot response

    Raises:
        HTTPException: If cry not found or belongs to different user
    """
    # Verify cry exists and belongs to user
    cry = db.query(CryInstance).filter(CryInstance.id == cry_id).first()

    if not cry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cry not found",
        )

    if cry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Save user message
    user_msg = ChatConversation(
        cry_instance_id=cry_id,
        message_text=request.message,
        sender="user",
    )
    db.add(user_msg)
    db.commit()

    # Generate bot response
    try:
        bot_response = await generate_advice(
            cry_id=cry_id,
            user_message=request.message,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}",
        )

    # Save bot message
    bot_msg = ChatConversation(
        cry_instance_id=cry_id,
        message_text=bot_response,
        sender="bot",
    )
    db.add(bot_msg)
    db.commit()

    return ChatMessageResponse(
        bot_response=bot_response,
        timestamp=bot_msg.timestamp.isoformat(),
    )


@router.get("/{cry_id}/history", response_model=List[ChatHistoryItem])
async def get_chat_history(
    cry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get chat history for a specific cry.

    Args:
        cry_id: Cry instance ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of chat messages

    Raises:
        HTTPException: If cry not found or belongs to different user
    """
    # Verify cry exists and belongs to user
    cry = db.query(CryInstance).filter(CryInstance.id == cry_id).first()

    if not cry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cry not found",
        )

    if cry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get chat messages
    messages = (
        db.query(ChatConversation)
        .filter(ChatConversation.cry_instance_id == cry_id)
        .order_by(ChatConversation.timestamp)
        .all()
    )

    return [
        ChatHistoryItem(
            message_id=msg.id,
            sender=msg.sender,
            message_text=msg.message_text,
            timestamp=msg.timestamp.isoformat(),
        )
        for msg in messages
    ]
