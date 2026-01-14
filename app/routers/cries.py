"""
Cry management endpoints.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, CryInstance, CryCategory
from app.utils.helpers import relative_time, format_timestamp
from app.utils.audio import validate_audio_file, convert_to_24khz_wav, save_uploaded_file
from app.ai.predictions import predict_cry_reason
import tempfile

router = APIRouter(prefix="/api/cries", tags=["cries"])


# Also add categories endpoint (should be at module level, not in /api/cries)
from fastapi import APIRouter as CategoryRouter
categories_router = APIRouter(prefix="/api", tags=["categories"])


@categories_router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """
    Get all cry categories.

    Returns:
        List of categories
    """
    categories = db.query(CryCategory).all()
    return [
        {
            "category_id": cat.id,
            "name": cat.name,
            "description": cat.description,
        }
        for cat in categories
    ]


# Response models
class CryHistoryItem(BaseModel):
    cry_id: int
    recorded_at: str  # ISO 8601
    recorded_at_relative: str
    category: Optional[str]
    category_id: Optional[int]
    category_source: Optional[str]
    notes: Optional[str]
    validation_status: Optional[bool]
    needs_labeling: bool
    has_audio: bool
    chat_message_count: int

    class Config:
        from_attributes = True


class CryDetailResponse(BaseModel):
    cry_id: int
    user_id: int
    audio_file_path: str
    recorded_at: str
    recorded_at_formatted: str
    category: Optional[str]
    category_id: Optional[int]
    category_source: Optional[str]
    notes: Optional[str]
    validation_status: Optional[bool]
    created_at: str

    class Config:
        from_attributes = True


class RecordResponse(BaseModel):
    cry_id: int
    status: str


class ValidationRequest(BaseModel):
    validation: bool
    category_id: Optional[int] = None
    notes: Optional[str] = None


class NotesUpdateRequest(BaseModel):
    notes: str


@router.post("/record", response_model=RecordResponse)
async def record_cry(
    audio_file: UploadFile = File(...),
    recorded_at: str = Form(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and process a new cry recording.

    Args:
        audio_file: Audio file (WAV, WebM, OGG, MP4, etc.)
        recorded_at: ISO 8601 timestamp of when recording was made
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        db: Database session

    Returns:
        Cry ID and processing status

    Raises:
        HTTPException: If file is invalid or processing fails
    """
    # Validate file
    validate_audio_file(audio_file)

    # Parse timestamp
    try:
        recorded_timestamp = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid timestamp format. Use ISO 8601.",
        )

    # Create temporary file for uploaded audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as temp_input:
        await save_uploaded_file(audio_file, temp_input.name)
        temp_input_path = temp_input.name

    try:
        # Create user directory
        audio_dir = os.getenv("AUDIO_FILES_DIR", "./audio_files")
        user_dir = os.path.join(audio_dir, f"user_{current_user.id}")
        os.makedirs(user_dir, exist_ok=True)

        # Generate temporary filename (will rename after getting cry_id)
        timestamp_str = recorded_timestamp.strftime("%Y%m%d_%H%M%S")
        temp_filename = f"{timestamp_str}_temp.wav"
        temp_output_path = os.path.join(user_dir, temp_filename)

        # Convert to 24kHz WAV
        convert_to_24khz_wav(temp_input_path, temp_output_path)

        # Create database record
        cry = CryInstance(
            user_id=current_user.id,
            audio_file_path=temp_output_path,
            recorded_at=recorded_timestamp,
        )
        db.add(cry)
        db.commit()
        db.refresh(cry)

        # Rename file with cry_id
        final_filename = f"{timestamp_str}_cry_{cry.id}.wav"
        final_path = os.path.join(user_dir, final_filename)
        os.rename(temp_output_path, final_path)

        # Update database with final path
        cry.audio_file_path = final_path
        db.commit()

        # Trigger AI prediction in background
        if background_tasks:
            background_tasks.add_task(predict_cry_reason, cry.id, current_user.id, db)

        return RecordResponse(
            cry_id=cry.id,
            status="processing" if background_tasks else "ready",
        )

    finally:
        # Clean up temporary file
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)


@router.get("/history", response_model=List[CryHistoryItem])
async def get_cry_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get cry history for the current user.

    Args:
        limit: Maximum number of results (default: 50, max: 100)
        offset: Pagination offset (default: 0)
        current_user: Authenticated user
        db: Database session

    Returns:
        List of cry instances
    """
    # Limit maximum results
    limit = min(limit, 100)

    # Query cry instances
    cries = (
        db.query(CryInstance)
        .filter(CryInstance.user_id == current_user.id)
        .order_by(desc(CryInstance.recorded_at))
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Build response
    result = []
    for cry in cries:
        # Get category name
        category_name = None
        if cry.category_id:
            category = db.query(CryCategory).filter(CryCategory.id == cry.category_id).first()
            if category:
                category_name = category.name

        # Count chat messages
        from app.models import ChatConversation
        chat_count = (
            db.query(func.count(ChatConversation.id))
            .filter(ChatConversation.cry_instance_id == cry.id)
            .scalar()
        )

        # Check if needs labeling (no category assigned)
        needs_labeling = cry.category_id is None

        result.append(
            CryHistoryItem(
                cry_id=cry.id,
                recorded_at=cry.recorded_at.isoformat(),
                recorded_at_relative=relative_time(cry.recorded_at),
                category=category_name,
                category_id=cry.category_id,
                category_source=cry.category_source,
                notes=cry.notes,
                validation_status=cry.validation_status,
                needs_labeling=needs_labeling,
                has_audio=os.path.exists(cry.audio_file_path) if cry.audio_file_path else False,
                chat_message_count=chat_count or 0,
            )
        )

    return result


@router.get("/{cry_id}", response_model=CryDetailResponse)
async def get_cry_detail(
    cry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific cry.

    Args:
        cry_id: Cry instance ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Cry instance details

    Raises:
        HTTPException: If cry not found or belongs to different user
    """
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

    # Get category name
    category_name = None
    if cry.category_id:
        category = db.query(CryCategory).filter(CryCategory.id == cry.category_id).first()
        if category:
            category_name = category.name

    return CryDetailResponse(
        cry_id=cry.id,
        user_id=cry.user_id,
        audio_file_path=cry.audio_file_path,
        recorded_at=cry.recorded_at.isoformat(),
        recorded_at_formatted=format_timestamp(cry.recorded_at),
        category=category_name,
        category_id=cry.category_id,
        category_source=cry.category_source,
        notes=cry.notes,
        validation_status=cry.validation_status,
        created_at=cry.created_at.isoformat(),
    )


@router.get("/{cry_id}/status")
async def get_cry_status(
    cry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get processing status for a cry.

    Returns status and prediction if available.
    """
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

    # Check if needs labeling
    if cry.category_id is None:
        return {
            "status": "ready",
            "needs_labeling": True,
        }

    # Has prediction
    category = db.query(CryCategory).filter(CryCategory.id == cry.category_id).first()

    # Get validated count for confidence
    validated_count = (
        db.query(CryInstance)
        .filter(
            CryInstance.user_id == current_user.id,
            CryInstance.validation_status == True,
        )
        .count()
    )

    return {
        "status": "ready",
        "needs_labeling": False,
        "prediction": {
            "category": category.name if category else "unknown",
            "category_id": cry.category_id,
            "notes": cry.notes,
            "confidence": "normal" if validated_count >= 5 else "low",
        },
    }


@router.put("/{cry_id}/validate")
async def validate_cry(
    cry_id: int,
    request: ValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validate or update a cry's category.

    Args:
        cry_id: Cry instance ID
        request: Validation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated cry details

    Raises:
        HTTPException: If cry not found or belongs to different user
    """
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

    if request.validation:
        # User confirms AI prediction is correct
        cry.validation_status = True
    else:
        # User corrects the prediction
        if not request.category_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="category_id required when validation is false",
            )

        # Verify category exists
        category = db.query(CryCategory).filter(CryCategory.id == request.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid category_id",
            )

        cry.category_id = request.category_id
        cry.category_source = "user"
        cry.validation_status = True

        if request.notes:
            cry.notes = request.notes

    db.commit()
    db.refresh(cry)

    # Get category name
    category_name = None
    if cry.category_id:
        category = db.query(CryCategory).filter(CryCategory.id == cry.category_id).first()
        if category:
            category_name = category.name

    return {
        "cry_id": cry.id,
        "category": category_name,
        "category_id": cry.category_id,
        "category_source": cry.category_source,
        "notes": cry.notes,
        "validation_status": cry.validation_status,
    }


@router.put("/{cry_id}/notes")
async def update_notes(
    cry_id: int,
    request: NotesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update notes for a cry.

    Args:
        cry_id: Cry instance ID
        request: Notes update data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated cry details

    Raises:
        HTTPException: If cry not found or belongs to different user
    """
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

    # Validate notes length
    if len(request.notes) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Notes too long (max 500 characters)",
        )

    cry.notes = request.notes
    db.commit()

    return {
        "cry_id": cry.id,
        "notes": cry.notes,
    }
