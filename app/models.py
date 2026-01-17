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
    embedding_stats = relationship("UserEmbeddingStats", back_populates="user", uselist=False, cascade="all, delete-orphan")


class CryInstance(Base):
    """Individual cry recording and analysis."""

    __tablename__ = "cry_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    audio_file_path = Column(String(500), nullable=False)
    photo_file_path = Column(String(500), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # AI-predicted reason and solution (not yet validated by user)
    ai_reason = Column(Text, nullable=True)
    ai_solution = Column(Text, nullable=True)

    # User-validated or user-entered reason for crying (e.g., "hungry", "tired", "dirty diaper")
    reason = Column(Text, nullable=True)
    reason_source = Column(
        String(10),
        CheckConstraint("reason_source IN ('user', 'ai')"),
        nullable=True,
    )

    # User-validated or user-entered solution that helped (e.g., "fed bottle", "rocked to sleep")
    solution = Column(Text, nullable=True)
    solution_source = Column(
        String(10),
        CheckConstraint("solution_source IN ('user', 'ai')"),
        nullable=True,
    )

    # Additional notes
    notes = Column(Text, nullable=True)

    # Validation status: NULL=not reviewed, TRUE=confirmed, FALSE=rejected
    validation_status = Column(Boolean, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="cry_instances")
    chat_conversations = relationship("ChatConversation", back_populates="cry_instance", cascade="all, delete-orphan")
    raw_embedding = relationship("CryEmbeddingRaw", back_populates="cry_instance", uselist=False, cascade="all, delete-orphan")


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


class CryEmbeddingRaw(Base):
    """Raw embeddings for cry instances (before user-level standardization)."""

    __tablename__ = "cry_embeddings_raw"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cry_id = Column(Integer, ForeignKey("cry_instances.id"), nullable=False, unique=True, index=True)
    embedding_json = Column(Text, nullable=False)  # JSON array of 1152 floats
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    cry_instance = relationship("CryInstance", back_populates="raw_embedding")


class UserEmbeddingStats(Base):
    """User-level embedding statistics for standardization."""

    __tablename__ = "user_embedding_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    mean_json = Column(Text, nullable=False)  # JSON array of 1152 floats
    std_json = Column(Text, nullable=False)   # JSON array of 1152 floats
    cry_count = Column(Integer, nullable=False, default=0)  # Number of cries used for stats
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="embedding_stats")
