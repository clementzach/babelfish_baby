"""
Audio processing utilities for file validation and conversion.
"""
from fastapi import UploadFile, HTTPException, status
from pydub import AudioSegment
import os
import tempfile


MAX_FILE_SIZE_MB = int(os.getenv("MAX_AUDIO_FILE_SIZE_MB", "10"))
MAX_DURATION_SECONDS = int(os.getenv("MAX_AUDIO_DURATION_SECONDS", "60"))


def validate_audio_file(file: UploadFile) -> None:
    """
    Validate uploaded audio file.

    Args:
        file: Uploaded file from request

    Raises:
        HTTPException: If file is invalid
    """
    # Check if file exists
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No file provided",
        )

    # Check content type (basic check)
    if file.content_type and not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type: {file.content_type}. Must be an audio file.",
        )


def convert_to_24khz_wav(input_path: str, output_path: str) -> None:
    """
    Convert audio file to 24kHz mono WAV format required by MERT model.

    Args:
        input_path: Path to input audio file
        output_path: Path to save converted WAV file

    Raises:
        HTTPException: If conversion fails or file is invalid
    """
    try:
        # Load audio file (pydub supports many formats)
        audio = AudioSegment.from_file(input_path)

        # Check duration
        duration_seconds = len(audio) / 1000.0
        if duration_seconds > MAX_DURATION_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Audio too long: {duration_seconds:.1f}s (max: {MAX_DURATION_SECONDS}s)",
            )

        if duration_seconds < 0.5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Audio too short: must be at least 0.5 seconds",
            )

        # Convert to 24kHz mono WAV
        audio = audio.set_frame_rate(24000)
        audio = audio.set_channels(1)  # Mono

        # Export as WAV
        audio.export(output_path, format="wav")

    except HTTPException:
        # Re-raise our own exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process audio file: {str(e)}",
        )


def get_audio_duration(file_path: str) -> float:
    """
    Get duration of audio file in seconds.

    Args:
        file_path: Path to audio file

    Returns:
        Duration in seconds
    """
    try:
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0
    except Exception:
        return 0.0


async def save_uploaded_file(file: UploadFile, destination: str) -> None:
    """
    Save uploaded file to destination.

    Args:
        file: Uploaded file
        destination: Destination file path
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    # Save file
    with open(destination, "wb") as f:
        content = await file.read()

        # Check file size
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large: {len(content) / 1024 / 1024:.1f}MB (max: {MAX_FILE_SIZE_MB}MB)",
            )

        f.write(content)
