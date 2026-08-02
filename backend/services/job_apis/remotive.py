"""Remotive job API client (free).

API docs: https://remotive.com/api/remote-jobs
Endpoint: https://remotive.com/api/remote-jobs
Rate limit: No documented limit
Returns: Curated remote jobs across categories
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.utils.constants import (
    HTTP_OK,
    JOB_API_TIMEOUT_SECONDS,
    REMOTIVE_BASE_URL,
    REMOTIVE_RESULT_LIMIT,
)
from backend.utils.dedup import generate_posting_id
from backend.utils.location_filter import filter_by_location
from backend.utils.text import unescape_html

logger = logging.getLogger(__name__)


class RemotiveClient:
    """Free remote jobs API (no key)."""

    def __init__(self) -> None:
        """No credentials; client is stateless."""

    async def search(self, preferences: Any) -> list[RawJobPosting]:
        """Search Remotive for remote jobs matching preferences."""
        # Remotive has no city/radius — skip when the user wants on-site only
        if not getattr(preferences, "remote_ok", False):
            logger.debug("Skipping Remotive: remote_ok is false")
            return []

        titles = getattr(preferences, "titles", None) or []
        if not titles:
            return []

        search_term = " ".join(titles)

        # Note: Remotive API does not support radius filtering.
        params: dict[str, str] = {
            "search": search_term,
            "limit": REMOTIVE_RESULT_LIMIT,
        }

        timeout = aiohttp.ClientTimeout(total=JOB_API_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(REMOTIVE_BASE_URL, params=params) as response:
                    if response.status != HTTP_OK:
                        logger.warning("Remotive HTTP %d", response.status)
                        return []
                    data = await response.json(content_type=None)
        except aiohttp.ClientError as e:
            logger.warning("Remotive connection error: %s", e)
            return []

        if not isinstance(data, dict):
            return []

        results: list[RawJobPosting] = []
        for item in data.get("jobs", []):
            try:
                title = unescape_html(item.get("title", ""))
                company = unescape_html(item.get("company_name", ""))
                loc = unescape_html(item.get("candidate_required_location", ""))
                url = item.get("url", "")
                description = unescape_html(item.get("description", ""))

                posting_id = generate_posting_id(title, company, loc)

                results.append(RawJobPosting(
                    id=posting_id,
                    title=title,
                    company=company,
                    location=loc or "Remote",
                    url=url,
                    description_text=description,
                    source="remotive",
                    date_posted=item.get("publication_date"),
                ))
            except (KeyError, ValueError) as e:
                logger.debug("Skipping Remotive item: %s", e)
                continue

        user_location = (
            preferences.location.split(",")[0].strip()
            if getattr(preferences, "location", None)
            else ""
        )
        before = len(results)
        results = filter_by_location(
            postings=results,
            user_location=user_location,
            remote_ok=getattr(preferences, "remote_ok", False),
        )
        if user_location:
            logger.debug(
                "Remotive location filter: %d → %d (location='%s', remote_ok=%s)",
                before,
                len(results),
                user_location,
                getattr(preferences, "remote_ok", False),
            )

        logger.debug("Remotive returned %d results", len(results))
        return results
