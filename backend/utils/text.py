"""Text helpers for API payloads and display."""
from __future__ import annotations

from html import unescape


def unescape_html(value: str | None) -> str:
    """Decode HTML entities (&amp; → &) from API title/company/description fields."""
    if not value:
        return ""
    return unescape(value)
