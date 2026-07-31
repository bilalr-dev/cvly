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
from backend.utils.dedup import generate_posting_id
from backend.utils.location_filter import filter_by_location

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowClient:
    """Free job board API (no key)."""

    def __init__(self) -> None:
        pass

    async def search(self, preferences: Any) -> list[RawJobPosting]:
        """Search Arbeitnow for jobs matching preferences."""
        search_term = " ".join(preferences.titles) if getattr(preferences, "titles", None) else "developer"
        location = preferences.location.split(",")[0].strip() if getattr(preferences, "location", None) else ""

        # Note: Arbeitnow API does not support radius filtering.
        params: dict[str, str] = {
            "search": search_term,
        }
        if location:
            params["location"] = location

        timeout = aiohttp.ClientTimeout(total=15)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(_BASE_URL, params=params) as response:
                    if response.status != 200:
                        logger.warning("Arbeitnow HTTP %d", response.status)
                        return []
                    data = await response.json(content_type=None)
        except aiohttp.ClientError as e:
            logger.warning("Arbeitnow connection error: %s", e)
            return []

        if not isinstance(data, dict):
            return []

        results: list[RawJobPosting] = []
        for item in data.get("data", []):
            try:
                title = item.get("title", "")
                company = item.get("company_name", "")
                loc = item.get("location", "")
                url = item.get("url", "")
                description = item.get("description", "")
                remote = item.get("remote", False)

                posting_id = generate_posting_id(title, company, loc)

                results.append(RawJobPosting(
                    id=posting_id,
                    title=title,
                    company=company,
                    location=loc if loc else ("Remote" if remote else ""),
                    url=url,
                    description_text=description,
                    source="arbeitnow",
                    date_posted=item.get("created_at"),
                ))
            except (KeyError, ValueError) as e:
                logger.debug("Skipping Arbeitnow item: %s", e)
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
                "Arbeitnow location filter: %d → %d (location='%s', remote_ok=%s)",
                before,
                len(results),
                user_location,
                getattr(preferences, "remote_ok", False),
            )

        logger.debug("Arbeitnow returned %d results", len(results))
        return results
