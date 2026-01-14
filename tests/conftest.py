"""
Pytest configuration and fixtures for end-to-end tests.
"""
import pytest
import subprocess
import time
import os
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def test_db():
    """Create a test database for the session."""
    # Use a separate test database
    test_db_path = "test_app.db"

    # Remove old test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # Set test database URL
    os.environ["DATABASE_URL"] = f"sqlite:///./{test_db_path}"

    # Initialize database
    subprocess.run(["python", "scripts/init_db.py"], check=True)

    yield test_db_path

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # Clean up test audio files
    test_audio_dir = "audio_files"
    if os.path.exists(test_audio_dir):
        shutil.rmtree(test_audio_dir)

    # Clean up test chroma db
    test_chroma_dir = "chroma_db"
    if os.path.exists(test_chroma_dir):
        shutil.rmtree(test_chroma_dir)


@pytest.fixture(scope="session")
def server(test_db):
    """Start the FastAPI server for testing."""
    import requests
    import sys

    # Start server in background (capture output to file for debugging)
    log_file = open("/tmp/test_server.log", "w")
    process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )

    # Wait for server to be ready (up to 10 seconds)
    server_ready = False
    for i in range(20):
        try:
            response = requests.get("http://127.0.0.1:8000/health", timeout=1)
            if response.status_code == 200:
                server_ready = True
                print("\n✓ Test server started successfully")
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(0.5)

    if not server_ready:
        # Print server output for debugging
        stdout, stderr = process.communicate(timeout=1)
        print(f"\nServer stdout: {stdout.decode()}")
        print(f"\nServer stderr: {stderr.decode()}")
        process.kill()
        raise RuntimeError("Test server failed to start")

    yield process

    # Cleanup: kill server
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture(scope="function")
def page(server, page):
    """Provide a fresh page for each test."""
    # page fixture comes from pytest-playwright
    page.goto("http://localhost:8000")
    yield page


@pytest.fixture
def unique_username():
    """Generate a unique username for testing."""
    import random
    import string
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"testuser_{suffix}"


@pytest.fixture
def test_credentials(unique_username):
    """Provide test credentials."""
    return {
        "username": unique_username,
        "password": "testpass123",
        "email": f"{unique_username}@test.com"
    }


def register_user(page, credentials):
    """Helper function to register a new user."""
    page.goto("http://localhost:8000")

    # Fill registration form
    page.fill('#register-username', credentials["username"])
    page.fill('#register-password', credentials["password"])
    if credentials.get("email"):
        page.fill('#register-email', credentials["email"])

    # Submit registration
    page.click('button:has-text("Register")')

    # Wait for redirect to history page
    page.wait_for_url("**/history", timeout=5000)


def login_user(page, credentials):
    """Helper function to log in a user."""
    page.goto("http://localhost:8000")

    # Fill login form
    page.fill('#login-username', credentials["username"])
    page.fill('#login-password', credentials["password"])

    # Submit login
    page.click('button:has-text("Login")')

    # Wait for redirect to history page
    page.wait_for_url("**/history", timeout=5000)


def create_fake_audio_file():
    """Create a fake audio file for testing."""
    import wave
    import numpy as np

    # Create a test audio file (1 second of sine wave)
    sample_rate = 24000
    duration = 1.0
    frequency = 440.0  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t)

    # Convert to 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)

    # Save to file
    filename = "/tmp/test_cry.wav"
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    return filename
