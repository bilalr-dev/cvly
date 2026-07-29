"""Arbeitnow job API client — free, no API key required.

API docs: https://www.arbeitnow.com/blog/job-board-api
Endpoint: https://www.arbeitnow.com/api/job-board-api
Rate limit: No documented limit (be respectful — max 1 req/sec)
Returns: Jobs from ATS systems (Greenhouse, Lever, Workday, SmartRecruiters)
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.utils.dedup import generate_posting_id

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowClient:
    """Free job board API — no API key needed."""

    def __init__(self) -> None:
        pass

    async def search(self, preferences: Any) -> list[RawJobPosting]:
        """Search Arbeitnow for jobs matching preferences."""
        search_term = " ".join(preferences.titles) if getattr(preferences, "titles", None) else "developer"
        location = preferences.location.split(",")[0].strip() if getattr(preferences, "location", None) else ""

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
                tags = item.get("tags", [])
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

        # Client-side location filter — API returns global results
        user_location = preferences.location.split(",")[0].strip().lower() if getattr(preferences, "location", None) else ""

        if user_location:
            location_filtered = []
            for posting in results:
                loc_lower = posting.location.lower()
                # Keep if location matches user's city/country
                if user_location in loc_lower:
                    location_filtered.append(posting)
                # Keep if posting is explicitly remote and user allows remote
                elif getattr(preferences, "remote_ok", False) and any(
                    kw in loc_lower for kw in ["remote", "télétravail", "anywhere", "worldwide"]
                ):
                    location_filtered.append(posting)
                # Drop everything else (USA, Canada, etc.)

            logger.info("Arbeitnow location filter: %d → %d (kept jobs near '%s')",
                       len(results), len(location_filtered), user_location)
            results = location_filtered

        logger.info("Arbeitnow returned %d results", len(results))
        return results
