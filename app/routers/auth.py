"""
Authentication endpoints: register, login, logout.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, create_session, destroy_session

router = APIRouter(prefix="/auth", tags=["authentication"])


# Request models
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=100)
    email: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    username: str
    password: str


# Response models
class AuthResponse(BaseModel):
    user_id: int
    username: str


@router.post("/register", response_model=AuthResponse)
def register(
    request: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.

    Args:
        request: Registration data (username, password, optional email)
        response: FastAPI Response object
        db: Database session

    Returns:
        User information (user_id, username)

    Raises:
        HTTPException: If username already exists
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Create new user
    user = User(
        username=request.username,
        password_hash=hash_password(request.password),
        email=request.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create session
    create_session(response, user.id)

    return AuthResponse(user_id=user.id, username=user.username)


@router.post("/login", response_model=AuthResponse)
def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Login with username and password.

    Args:
        request: Login credentials (username, password)
        response: FastAPI Response object
        db: Database session

    Returns:
        User information (user_id, username)

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create session
    create_session(response, user.id)

    return AuthResponse(user_id=user.id, username=user.username)


@router.post("/logout")
def logout(response: Response):
    """
    Logout current user by destroying session.

    Args:
        response: FastAPI Response object

    Returns:
        Success message
    """
    destroy_session(response)
    return {"success": True}
