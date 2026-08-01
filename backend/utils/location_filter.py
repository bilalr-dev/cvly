"""Shared client-side location filter for job API clients."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.job import RawJobPosting

_DEFAULT_REMOTE_KEYWORDS: tuple[str, ...] = (
    "remote",
    "anywhere",
    "worldwide",
    "europe",
    "eu",
    "emea",
    "télétravail",
)


def filter_by_location(
    postings: list[RawJobPosting],
    user_location: str,
    remote_ok: bool,
    remote_keywords: tuple[str, ...] = _DEFAULT_REMOTE_KEYWORDS,
) -> list[RawJobPosting]:
    """Keep only postings matching the user's location or remote preference."""
    if not user_location:
        return postings

    location_lower = user_location.lower()
    return [
        posting
        for posting in postings
        if location_lower in posting.location.lower()
        or (remote_ok and any(kw in posting.location.lower() for kw in remote_keywords))
    ]
