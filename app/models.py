"""
SQLAlchemy ORM models for the application.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    cry_instances = relationship("CryInstance", back_populates="user", cascade="all, delete-orphan")


class CryInstance(Base):
    """Individual cry recording and analysis."""

    __tablename__ = "cry_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    audio_file_path = Column(String(500), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    reason_source = Column(
        String(10),
        CheckConstraint("category_source IN ('user', 'ai')"),
        nullable=True,
    )
    solution = Column(Text, nullable=True)
    solution_source = Column(
        String(10),
        CheckConstraint("category_source IN ('user', 'ai')"),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
    validation_status = Column(Boolean, nullable=True, index=True)  # NULL=not reviewed, TRUE=confirmed, FALSE=rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="cry_instances")
    chat_conversations = relationship("ChatConversation", back_populates="cry_instance", cascade="all, delete-orphan")


class ChatConversation(Base):
    """Chat messages between user and AI bot about a specific cry."""

    __tablename__ = "chat_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cry_instance_id = Column(Integer, ForeignKey("cry_instances.id"), nullable=False, index=True)
    message_text = Column(Text, nullable=False)
    sender = Column(
        String(10),
        CheckConstraint("sender IN ('user', 'bot')"),
        nullable=False,
    )
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    cry_instance = relationship("CryInstance", back_populates="chat_conversations")
