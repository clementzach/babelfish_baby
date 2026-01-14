"""
Tests for system dependencies and requirements.
"""
import pytest
import shutil
import subprocess
from app.utils.system_checks import check_ffmpeg_installed, get_ffmpeg_version


def test_ffmpeg_is_installed():
    """Test that ffmpeg is installed and accessible."""
    is_installed, message = check_ffmpeg_installed()

    assert is_installed, (
        f"ffmpeg is not installed!\n\n"
        f"{message}\n\n"
        f"Audio recording features require ffmpeg to be installed."
    )


def test_ffprobe_is_installed():
    """Test that ffprobe is installed and accessible."""
    ffprobe_path = shutil.which("ffprobe")

    assert ffprobe_path is not None, (
        "ffprobe is not installed!\n\n"
        "To install:\n"
        "  macOS:   brew install ffmpeg\n"
        "  Ubuntu:  sudo apt-get install ffmpeg\n"
        "  Windows: Download from https://ffmpeg.org/download.html\n\n"
        "ffprobe is required for audio file processing."
    )


def test_ffmpeg_works():
    """Test that ffmpeg can be executed successfully."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, f"ffmpeg returned error code {result.returncode}"
        assert "ffmpeg version" in result.stdout.lower(), "ffmpeg version output not found"
    except FileNotFoundError:
        pytest.fail("ffmpeg command not found in PATH")
    except subprocess.TimeoutExpired:
        pytest.fail("ffmpeg command timed out")
    except Exception as e:
        pytest.fail(f"Error running ffmpeg: {str(e)}")


def test_get_ffmpeg_version():
    """Test getting ffmpeg version information."""
    version_info = get_ffmpeg_version()

    assert version_info is not None
    assert len(version_info) > 0

    # If installed, should contain version info
    is_installed, _ = check_ffmpeg_installed()
    if is_installed:
        assert "ffmpeg" in version_info.lower()


def test_audio_processing_dependencies():
    """Test that all audio processing dependencies are available."""
    # Check pydub can be imported
    try:
        from pydub import AudioSegment
        from pydub.utils import which

        # Check pydub can find ffmpeg/ffprobe
        ffmpeg = which("ffmpeg")
        ffprobe = which("ffprobe")

        assert ffmpeg is not None, "pydub cannot find ffmpeg"
        assert ffprobe is not None, "pydub cannot find ffprobe"

    except ImportError as e:
        pytest.fail(f"Failed to import audio processing libraries: {str(e)}")


@pytest.mark.skipif(
    not shutil.which("ffmpeg"),
    reason="ffmpeg not installed - skipping audio conversion test"
)
def test_audio_conversion_smoke_test():
    """Smoke test for audio conversion functionality."""
    import tempfile
    import wave
    import numpy as np
    from app.utils.audio import convert_to_24khz_wav

    # Create a simple test audio file (1 second of sine wave)
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t)
    audio_data = (audio_data * 32767).astype(np.int16)

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_input:
        input_path = temp_input.name

        with wave.open(input_path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

    # Test conversion
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_output:
        output_path = temp_output.name

    try:
        # This should not raise an exception if ffmpeg is working
        convert_to_24khz_wav(input_path, output_path)

        # Verify output file was created
        import os
        assert os.path.exists(output_path), "Output file was not created"
        assert os.path.getsize(output_path) > 0, "Output file is empty"

        # Verify it's a valid WAV file with correct sample rate
        with wave.open(output_path, 'r') as wav_file:
            assert wav_file.getframerate() == 24000, "Output sample rate is not 24kHz"
            assert wav_file.getnchannels() == 1, "Output is not mono"

    finally:
        # Cleanup
        import os
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)
