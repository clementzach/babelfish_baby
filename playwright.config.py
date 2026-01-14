"""
Playwright configuration for end-to-end tests.
"""
from playwright.sync_api import Browser, BrowserContext, Page
import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with permissions."""
    return {
        **browser_context_args,
        "permissions": ["microphone"],
        "viewport": {"width": 1280, "height": 720},
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch arguments."""
    return {
        **browser_type_launch_args,
        "headless": True,
        "args": [
            "--use-fake-ui-for-media-stream",  # Auto-allow microphone
            "--use-fake-device-for-media-stream",  # Use fake audio
        ],
    }
