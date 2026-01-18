"""
Photo file validation and processing utilities.
"""
import os
from fastapi import HTTPException, status, UploadFile
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

# Try to import pillow-heif for HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
    logger.info("[Photo] HEIC support enabled via pillow-heif")
except ImportError:
    HEIC_SUPPORT = False
    logger.warning("[Photo] pillow-heif not installed - HEIC files will not be supported")

# Allowed photo formats
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
ALLOWED_PHOTO_MIMETYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/octet-stream",  # iOS sometimes sends HEIC as this
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


async def save_uploaded_photo(photo_file: UploadFile, output_path: str) -> str:
    """
    Save uploaded photo to disk. If photo is HEIC/HEIF, it will be converted to JPG.

    Args:
        photo_file: Uploaded photo file
        output_path: Destination file path

    Returns:
        The actual path where the file was saved (may differ if HEIC was converted to JPG)

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

    # Open and verify the image
    logger.info("[Photo Save] Opening and verifying image...")
    try:
        image = Image.open(io.BytesIO(content))
        image_format = image.format
        image_size = image.size
        logger.info(f"[Photo Save] Image opened: format={image_format}, size={image_size}")

        # Check if it's a HEIC file that needs conversion
        is_heic = image_format in ['HEIF', 'HEIC'] or output_path.lower().endswith(('.heic', '.heif'))

        if is_heic:
            logger.info("[Photo Save] HEIC/HEIF detected, converting to JPG...")
            # Convert to JPG
            # Need to re-open since verify() consumes the image
            image = Image.open(io.BytesIO(content))

            # Convert to RGB (HEIC might be in a different color space)
            if image.mode != 'RGB':
                logger.info(f"[Photo Save] Converting from {image.mode} to RGB")
                image = image.convert('RGB')

            # Change output path to .jpg
            output_path = os.path.splitext(output_path)[0] + '.jpg'
            logger.info(f"[Photo Save] Updated output path to: {output_path}")

            # Save as JPG to a BytesIO buffer
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=90)
            content = output_buffer.getvalue()
            logger.info(f"[Photo Save] Converted to JPG, new size: {len(content)} bytes")
        else:
            # For non-HEIC images, just verify
            image.verify()
            logger.info(f"[Photo Save] Image verified: {image_format}")

    except Exception as e:
        logger.error(f"[Photo Save] Image processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid or corrupted image file: {str(e)}",
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

    # Return the actual path (may have changed from .heic to .jpg)
    return output_path


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
