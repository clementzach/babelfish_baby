"""
Authentication utilities for password hashing and session management.
"""
from passlib.context import CryptContext
from fastapi import Response
import os

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session configuration
SESSION_COOKIE_NAME = "session"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Previously hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_session(response: Response, user_id: int):
    """
    Create a session by setting a session cookie.

    Args:
        response: FastAPI Response object
        user_id: User ID to store in session
    """
    import logging
    logger = logging.getLogger(__name__)

    # For MVP, we'll use a simple approach with signed cookies
    # In production, consider using a proper session management library

    # Get root path for reverse proxy support
    root_path = os.getenv("ROOT_PATH", "")
    # Normalize path - ensure it starts with / and doesn't end with / unless it's root
    if root_path:
        cookie_path = root_path if root_path.endswith("/") else root_path + "/"
    else:
        cookie_path = "/"

    # Use secure cookies in production (when HTTPS is available)
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    logger.info(f"[Auth] Creating session for user {user_id}")
    logger.info(f"[Auth] Cookie path: {cookie_path}, secure: {is_production}")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=str(user_id),
        httponly=True,
        max_age=30 * 24 * 60 * 60,  # 30 days
        samesite="lax",
        secure=is_production,  # Enable in production with HTTPS
        path=cookie_path,  # Set path for reverse proxy
    )

    logger.info(f"[Auth] Session cookie set successfully")


def destroy_session(response: Response):
    """
    Destroy a session by deleting the session cookie.

    Args:
        response: FastAPI Response object
    """
    import logging
    logger = logging.getLogger(__name__)

    # Get root path for reverse proxy support
    root_path = os.getenv("ROOT_PATH", "")
    # Normalize path - ensure it starts with / and doesn't end with / unless it's root
    if root_path:
        cookie_path = root_path if root_path.endswith("/") else root_path + "/"
    else:
        cookie_path = "/"

    logger.info(f"[Auth] Destroying session, cookie path: {cookie_path}")
    response.delete_cookie(key=SESSION_COOKIE_NAME, path=cookie_path)
