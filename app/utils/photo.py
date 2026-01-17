"""
Photo file validation and processing utilities.
"""
import os
from fastapi import HTTPException, status, UploadFile
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

# Allowed photo formats
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PHOTO_MIMETYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Size limits
MAX_PHOTO_FILE_SIZE_MB = 10
MAX_PHOTO_FILE_SIZE_BYTES = MAX_PHOTO_FILE_SIZE_MB * 1024 * 1024


def validate_photo_file(photo_file: UploadFile) -> None:
    """
    Validate uploaded photo file.

    Args:
        photo_file: Uploaded photo file from FastAPI

    Raises:
        HTTPException: If file is invalid
    """
    logger.info(f"[Photo Validation] Starting validation")
    logger.info(f"[Photo Validation] Filename: {photo_file.filename if photo_file else 'None'}")
    logger.info(f"[Photo Validation] Content-Type: {photo_file.content_type if photo_file else 'None'}")

    if not photo_file:
        logger.info("[Photo Validation] No photo file provided (optional)")
        return  # Photo is optional

    # Check file extension
    file_ext = os.path.splitext(photo_file.filename)[1].lower()
    logger.info(f"[Photo Validation] Extension: {file_ext}")

    if file_ext not in ALLOWED_PHOTO_EXTENSIONS:
        logger.error(f"[Photo Validation] Invalid extension: {file_ext}, allowed: {ALLOWED_PHOTO_EXTENSIONS}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid photo format. Allowed: {', '.join(ALLOWED_PHOTO_EXTENSIONS)}",
        )

    # Check MIME type
    if photo_file.content_type not in ALLOWED_PHOTO_MIMETYPES:
        logger.error(f"[Photo Validation] Invalid MIME type: {photo_file.content_type}, allowed: {ALLOWED_PHOTO_MIMETYPES}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid photo MIME type. Allowed: {', '.join(ALLOWED_PHOTO_MIMETYPES)}",
        )

    logger.info("[Photo Validation] Validation passed")


async def save_uploaded_photo(photo_file: UploadFile, output_path: str) -> None:
    """
    Save uploaded photo to disk.

    Args:
        photo_file: Uploaded photo file
        output_path: Destination file path

    Raises:
        HTTPException: If save fails or file is too large
    """
    logger.info(f"[Photo Save] Starting save to {output_path}")

    # Read file content
    logger.info("[Photo Save] Reading file content...")
    content = await photo_file.read()
    content_size = len(content)
    logger.info(f"[Photo Save] Read {content_size} bytes ({content_size / 1024 / 1024:.2f} MB)")

    # Check file size
    if content_size > MAX_PHOTO_FILE_SIZE_BYTES:
        logger.error(f"[Photo Save] File too large: {content_size} bytes (max: {MAX_PHOTO_FILE_SIZE_BYTES})")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Photo file too large. Maximum size: {MAX_PHOTO_FILE_SIZE_MB}MB",
        )

    # Verify it's a valid image
    logger.info("[Photo Save] Verifying image integrity...")
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()  # Verify it's a valid image
        logger.info(f"[Photo Save] Image verified: {image.format}, size: {image.size}")
    except Exception as e:
        logger.error(f"[Photo Save] Image verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or corrupted image file",
        )

    # Save to disk
    logger.info(f"[Photo Save] Writing to disk: {output_path}")
    try:
        with open(output_path, "wb") as f:
            f.write(content)
        logger.info(f"[Photo Save] Successfully saved to disk")

        # Verify file was written
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"[Photo Save] File verified on disk: {file_size} bytes")
        else:
            logger.error(f"[Photo Save] File not found after write: {output_path}")
    except Exception as e:
        logger.error(f"[Photo Save] Failed to write file: {e}")
        raise


def get_photo_base64(photo_path: str) -> str:
    """
    Read photo file and convert to base64 string for OpenAI API.

    Args:
        photo_path: Path to photo file

    Returns:
        Base64-encoded string of the photo

    Raises:
        FileNotFoundError: If photo doesn't exist
    """
    import base64

    if not os.path.exists(photo_path):
        raise FileNotFoundError(f"Photo file not found: {photo_path}")

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    return base64.b64encode(photo_bytes).decode("utf-8")


def get_photo_mimetype(photo_path: str) -> str:
    """
    Get MIME type from photo file extension.

    Args:
        photo_path: Path to photo file

    Returns:
        MIME type string (e.g., "image/jpeg")
    """
    ext = os.path.splitext(photo_path)[1].lower()

    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    return mime_map.get(ext, "image/jpeg")
