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
from backend.utils.dedup import generate_posting_id

logger = logging.getLogger(__name__)

_BASE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveClient:
    """Free remote jobs API (no key)."""

    def __init__(self) -> None:
        pass

    async def search(self, preferences: Any) -> list[RawJobPosting]:
        """Search Remotive for remote jobs matching preferences."""
        search_term = " ".join(preferences.titles) if getattr(preferences, "titles", None) else "developer"

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

        # Client-side location filter
        user_location = preferences.location.split(",")[0].strip().lower() if getattr(preferences, "location", None) else ""
        remote_ok = getattr(preferences, "remote_ok", False)

        if user_location:
            location_filtered = []
            for posting in results:
                loc_lower = posting.location.lower()

                # Keep if location mentions user's city or country
                if user_location in loc_lower:
                    location_filtered.append(posting)
                    continue

                # Only keep remote/worldwide if user explicitly allows remote
                if remote_ok:
                    location_filtered.append(posting)
                    continue

                # Remote is OFF — drop everything that doesn't match the city

            logger.debug("Remotive location filter: %d → %d (location='%s', remote_ok=%s)",
                       len(results), len(location_filtered), user_location, remote_ok)
            results = location_filtered

        logger.debug("Remotive returned %d results", len(results))
        return results
