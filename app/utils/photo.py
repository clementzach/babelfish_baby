"""
Photo file validation and processing utilities.
"""
import os
from fastapi import HTTPException, status, UploadFile
from PIL import Image
import io

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
    if not photo_file:
        return  # Photo is optional

    # Check file extension
    file_ext = os.path.splitext(photo_file.filename)[1].lower()
    if file_ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid photo format. Allowed: {', '.join(ALLOWED_PHOTO_EXTENSIONS)}",
        )

    # Check MIME type
    if photo_file.content_type not in ALLOWED_PHOTO_MIMETYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid photo MIME type. Allowed: {', '.join(ALLOWED_PHOTO_MIMETYPES)}",
        )


async def save_uploaded_photo(photo_file: UploadFile, output_path: str) -> None:
    """
    Save uploaded photo to disk.

    Args:
        photo_file: Uploaded photo file
        output_path: Destination file path

    Raises:
        HTTPException: If save fails or file is too large
    """
    # Read file content
    content = await photo_file.read()

    # Check file size
    if len(content) > MAX_PHOTO_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Photo file too large. Maximum size: {MAX_PHOTO_FILE_SIZE_MB}MB",
        )

    # Verify it's a valid image
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()  # Verify it's a valid image
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or corrupted image file",
        )

    # Save to disk
    with open(output_path, "wb") as f:
        f.write(content)


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
