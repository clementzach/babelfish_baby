"""
FastAPI dependencies for authentication and database access.
"""
from __future__ import annotations
from fastapi import Cookie, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import SESSION_COOKIE_NAME
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_current_user(
    session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the currently authenticated user.

    Args:
        session: Session cookie value
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If not authenticated or user not found
    """
    logger.info(f"[Auth Check] Session cookie value: {session if session else 'None'}")

    if not session:
        logger.warning("[Auth Check] No session cookie found - returning 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_id = int(session)
        logger.info(f"[Auth Check] Parsed user_id: {user_id}")
    except ValueError:
        logger.error(f"[Auth Check] Invalid session value: {session}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"[Auth Check] User not found in database: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    logger.info(f"[Auth Check] Successfully authenticated user: {user.username} (id={user.id})")
    return user


def get_current_user_optional(
    session: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Dependency to get the currently authenticated user, or None if not authenticated.

    Args:
        session: Session cookie value
        db: Database session

    Returns:
        User object or None
    """
    if not session:
        return None

    try:
        user_id = int(session)
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except (ValueError, Exception):
        return None
