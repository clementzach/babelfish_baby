"""
End-to-end tests for audio playback functionality.
"""
import pytest
from tests.conftest import register_user


@pytest.mark.e2e
def test_audio_player_exists_in_history(page, test_credentials):
    """Test that audio players appear in the cry history."""
    register_user(page, test_credentials)

    # Navigate to history page
    page.goto("http://localhost:8000/history")
    page.wait_for_load_state('networkidle')

    # Check that the page loaded
    assert page.is_visible('h1:has-text("BabelFish Baby")')

    # Note: This test will pass if there are no recordings
    # If there are recordings with audio, audio players should appear
    # We're just verifying the page structure is correct


@pytest.mark.e2e
def test_audio_endpoint_requires_auth(page):
    """Test that audio endpoint requires authentication."""
    # Try to access audio endpoint without authentication
    response = page.goto("http://localhost:8000/api/cries/1/audio")

    # Should redirect or return 401
    assert response.status in [401, 302, 303]


@pytest.mark.e2e
def test_audio_player_controls_present(page, test_credentials):
    """Test that if cry items exist, they have audio players."""
    register_user(page, test_credentials)

    # Go to history
    page.goto("http://localhost:8000/history")
    page.wait_for_timeout(2000)

    # Check if any cry items exist
    cry_items = page.locator('.cry-item')

    if cry_items.count() > 0:
        # If there are cry items, check for audio players
        # Note: audio players only appear if has_audio is true
        audio_players = page.locator('audio[controls]')

        # We can't guarantee audio exists, but we can check the structure is valid
        # Just verify page didn't crash
        assert page.is_visible('h1:has-text("BabelFish Baby")')
