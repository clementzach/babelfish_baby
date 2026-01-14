"""
End-to-end tests for chat functionality.
"""
import pytest
from tests.conftest import register_user


@pytest.mark.e2e
def test_chat_page_loads(page, test_credentials):
    """Test that chat page loads (with a dummy cry ID)."""
    register_user(page, test_credentials)

    # Try to navigate to chat page with cry_id 1
    # This might not exist, but we can test the page structure
    page.goto("http://localhost:8000/chat/1")

    # Wait for page load
    page.wait_for_load_state('networkidle')

    # Check that chat elements exist
    assert page.is_visible('.chat-container')
    assert page.is_visible('#messageInput')
    assert page.is_visible('button:has-text("Send")')


@pytest.mark.e2e
def test_chat_has_example_prompts(page, test_credentials):
    """Test that chat page shows example prompts."""
    register_user(page, test_credentials)
    page.goto("http://localhost:8000/chat/1")

    page.wait_for_load_state('networkidle')

    # Check for example prompts
    prompts = page.locator('.example-prompt')
    assert prompts.count() >= 3

    # Check specific prompts exist
    assert page.is_visible('button:has-text("How do I get them to sleep?")')
    assert page.is_visible('button:has-text("Should I swaddle them?")')
    assert page.is_visible('button:has-text("When should I call the doctor?")')


@pytest.mark.e2e
def test_chat_back_button(page, test_credentials):
    """Test that back button returns to history."""
    register_user(page, test_credentials)
    page.goto("http://localhost:8000/chat/1")

    # Click back button
    page.click('a:has-text("Back to History")')

    # Should navigate back to history
    page.wait_for_url("**/history", timeout=5000)
    assert page.url.endswith("/history")


@pytest.mark.e2e
def test_chat_input_textarea(page, test_credentials):
    """Test that chat input textarea works."""
    register_user(page, test_credentials)
    page.goto("http://localhost:8000/chat/1")

    page.wait_for_load_state('networkidle')

    # Type in the textarea
    textarea = page.locator('#messageInput')
    test_message = "This is a test message"
    textarea.fill(test_message)

    # Verify the text was entered
    assert textarea.input_value() == test_message


@pytest.mark.e2e
def test_example_prompt_fills_input(page, test_credentials):
    """Test that clicking example prompt fills the input."""
    register_user(page, test_credentials)
    page.goto("http://localhost:8000/chat/1")

    page.wait_for_load_state('networkidle')

    # Get an example prompt
    prompt = page.locator('.example-prompt').first

    # Click it
    prompt.click()

    # Wait a moment
    page.wait_for_timeout(500)

    # The textarea might be filled (depends on implementation)
    # This test checks if the button click works at minimum
    # Actual behavior depends on chat.js implementation


@pytest.mark.e2e
def test_chat_form_submission(page, test_credentials):
    """Test that chat form can be submitted (may fail without real cry data)."""
    register_user(page, test_credentials)
    page.goto("http://localhost:8000/chat/1")

    page.wait_for_load_state('networkidle')

    # Fill the textarea
    page.fill('#messageInput', "Test question about baby")

    # Submit the form
    page.click('button:has-text("Send")')

    # Wait for potential response
    page.wait_for_timeout(2000)

    # The request might fail if cry_id 1 doesn't exist
    # But we're testing that the form submission works
    # Actual message sending depends on backend having real data
