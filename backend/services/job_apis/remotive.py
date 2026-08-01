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
from backend.utils.constants import DEFAULT_JOB_SEARCH_TERM
from backend.utils.dedup import generate_posting_id
from backend.utils.location_filter import filter_by_location

logger = logging.getLogger(__name__)

_BASE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveClient:
    """Free remote jobs API (no key)."""

    def __init__(self) -> None:
        pass

    async def search(self, preferences: Any) -> list[RawJobPosting]:
        """Search Remotive for remote jobs matching preferences."""
        search_term = (
            " ".join(preferences.titles)
            if getattr(preferences, "titles", None)
            else DEFAULT_JOB_SEARCH_TERM
        )

        # Note: Remotive API does not support radius filtering.
        params: dict[str, str] = {
            "search": search_term,
            "limit": "50",
        }

        timeout = aiohttp.ClientTimeout(total=15)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(_BASE_URL, params=params) as response:
                    if response.status != 200:
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
                title = item.get("title", "")
                company = item.get("company_name", "")
                loc = item.get("candidate_required_location", "")
                url = item.get("url", "")
                description = item.get("description", "")

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
