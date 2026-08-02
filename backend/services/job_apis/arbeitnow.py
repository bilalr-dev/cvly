"""Arbeitnow job API client (free).

API docs: https://www.arbeitnow.com/blog/job-board-api
Endpoint: https://www.arbeitnow.com/api/job-board-api
Rate limit: No documented limit (be respectful).
Returns: Jobs from ATS systems (Greenhouse, Lever, Workday, SmartRecruiters)
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.utils.constants import (
    ARBEITNOW_BASE_URL,
    HTTP_OK,
    JOB_API_TIMEOUT_SECONDS,
)
from backend.utils.dedup import generate_posting_id
from backend.utils.location_filter import filter_by_location
from backend.utils.text import unescape_html

logger = logging.getLogger(__name__)


def _parse_arbeitnow_item(item: dict[str, Any]) -> RawJobPosting | None:
    try:
        title = unescape_html(item.get("title", ""))
        company = unescape_html(item.get("company_name", ""))
        loc = unescape_html(item.get("location", ""))
        if loc:
            location = loc
        elif item.get("remote", False):
            location = "Remote"
        else:
            location = ""
        return RawJobPosting(
            id=generate_posting_id(title, company, loc),
            title=title,
            company=company,
            location=location,
            url=item.get("url", ""),
            description_text=unescape_html(item.get("description", "")),
            source="arbeitnow",
            date_posted=item.get("created_at"),
        )
    except (KeyError, ValueError) as e:
        logger.debug("Skipping Arbeitnow item: %s", e)
        return None


class ArbeitnowClient:
    """Free job board API (no key)."""

    def __init__(self) -> None:
        """No credentials; client is stateless."""

    async def search(self, preferences: Any) -> list[RawJobPosting]:
        """Search Arbeitnow for jobs matching preferences."""
        # Remote-first board: skip when the user wants on-site only
        if not getattr(preferences, "remote_ok", False):
            logger.debug("Skipping Arbeitnow: remote_ok is false")
            return []

        titles = getattr(preferences, "titles", None) or []
        if not titles:
            return []

        search_term = " ".join(titles)
        location = (
            preferences.location.split(",")[0].strip()
            if getattr(preferences, "location", None)
            else ""
        )

        # Note: Arbeitnow API does not support radius filtering.
        params: dict[str, str] = {"search": search_term}
        if location:
            params["location"] = location

        timeout = aiohttp.ClientTimeout(total=JOB_API_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:  # noqa: SIM117
                async with session.get(ARBEITNOW_BASE_URL, params=params) as response:
                    if response.status != HTTP_OK:
                        logger.warning("Arbeitnow HTTP %d", response.status)
                        return []
                    data = await response.json(content_type=None)
        except aiohttp.ClientError as e:
            logger.warning("Arbeitnow connection error: %s", e)
            return []

        if not isinstance(data, dict):
            return []

        results = [
            posting
            for item in data.get("data", [])
            if (posting := _parse_arbeitnow_item(item)) is not None
        ]

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
                "Arbeitnow location filter: %d → %d (location='%s', remote_ok=%s)",
                before,
                len(results),
                user_location,
                getattr(preferences, "remote_ok", False),
            )

        logger.debug("Arbeitnow returned %d results", len(results))
        return results
