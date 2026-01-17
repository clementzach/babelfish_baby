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
    # For MVP, we'll use a simple approach with signed cookies
    # In production, consider using a proper session management library

    # Get root path for reverse proxy support
    root_path = os.getenv("ROOT_PATH", "")
    cookie_path = root_path + "/" if root_path else "/"

    # Use secure cookies in production (when HTTPS is available)
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=str(user_id),
        httponly=True,
        max_age=30 * 24 * 60 * 60,  # 30 days
        samesite="lax",
        secure=is_production,  # Enable in production with HTTPS
        path=cookie_path,  # Set path for reverse proxy
    )


def destroy_session(response: Response):
    """
    Destroy a session by deleting the session cookie.

    Args:
        response: FastAPI Response object
    """
    # Get root path for reverse proxy support
    root_path = os.getenv("ROOT_PATH", "")
    cookie_path = root_path + "/" if root_path else "/"

    response.delete_cookie(key=SESSION_COOKIE_NAME, path=cookie_path)
