"""
Helper utilities for time formatting and other common tasks.
"""
from datetime import datetime, timezone
from typing import Optional


def relative_time(timestamp: datetime) -> str:
    """
    Convert timestamp to relative time format (e.g., "2 hours ago").

    Args:
        timestamp: Datetime object to convert

    Returns:
        Relative time string
    """
    # Ensure timestamp is timezone-aware
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - timestamp

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def format_timestamp(timestamp: datetime) -> str:
    """
    Format timestamp for display.

    Args:
        timestamp: Datetime object to format

    Returns:
        Formatted string like "Jan 10, 2026 at 2:30 PM"
    """
    return timestamp.strftime("%b %d, %Y at %I:%M %p")


def get_category_css_class(category_name: Optional[str]) -> str:
    """
    Get CSS class for a category badge.

    Args:
        category_name: Name of the category

    Returns:
        CSS class name
    """
    if not category_name:
        return "category-other"

    return f"category-{category_name.lower()}"
