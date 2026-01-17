"""
System dependency checks for the application.
"""
import shutil
import subprocess
from typing import Tuple


def check_ffmpeg_installed() -> Tuple[bool, str]:
    """
    Check if ffmpeg/ffprobe is installed and accessible.

    Returns:
        Tuple of (is_installed, message)
    """
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    if not ffmpeg_path or not ffprobe_path:
        missing = []
        if not ffmpeg_path:
            missing.append("ffmpeg")
        if not ffprobe_path:
            missing.append("ffprobe")

        message = f"Missing required audio tools: {', '.join(missing)}\n\n"
        message += "To install:\n"
        message += "  macOS:   brew install ffmpeg\n"
        message += "  Ubuntu:  sudo apt-get install ffmpeg\n"
        message += "  Windows: Download from https://ffmpeg.org/download.html"

        return False, message

    # Try to get version to verify it works
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return True, f"ffmpeg is installed: {version_line}"
        else:
            return False, "ffmpeg found but not working correctly"
    except Exception as e:
        return False, f"ffmpeg found but error checking version: {str(e)}"


def get_ffmpeg_version() -> str:
    """
    Get ffmpeg version string.

    Returns:
        Version string or error message
    """
    is_installed, message = check_ffmpeg_installed()
    return message
