"""Jobicy remote-jobs client (free, no API key).

API docs: https://jobicy.com/jobs-rss-feed
Endpoint: https://jobicy.com/api/v2/remote-jobs
Params: count (1-100), geo (region), tag (keyword search)
Returns: Remote jobs across industries, EU/US focus.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.config import get_settings
from backend.models.job import RawJobPosting
from backend.utils.constants import (
    COUNTRY_GEO_MAP,
    HTTP_OK,
    JOB_API_TIMEOUT_SECONDS,
    JOBICY_BASE_URL,
    JOBICY_DEFAULT_COUNT,
    JOBICY_JOB_PAGE_URL,
)
from backend.utils.dedup import generate_posting_id
from backend.utils.location_filter import filter_by_location

logger = logging.getLogger(__name__)


def _build_search_params(preferences: Any) -> dict[str, str] | None:
    titles = getattr(preferences, "titles", None) or []
    if not titles:
        return None
    country = (getattr(preferences, "country", None) or get_settings().default_country).upper()
    return {
        "count": JOBICY_DEFAULT_COUNT,
        "tag": " ".join(titles),
        "geo": COUNTRY_GEO_MAP.get(country, "europe"),
    }


def _parse_jobicy_item(item: dict[str, Any]) -> RawJobPosting | None:
    try:
        title = item.get("jobTitle", "")
        company = item.get("companyName", "")
        loc = item.get("jobGeo", "")

        # Prefer the web job page; some feed URLs omit /jobs/ and serve raw content
        url = item.get("url", "") or ""
        if url and "/jobs/" not in url:
            job_slug = item.get("jobSlug") or item.get("id")
            if job_slug:
                url = JOBICY_JOB_PAGE_URL.format(slug=job_slug)

        return RawJobPosting(
            id=generate_posting_id(title, company, loc),
            title=title,
            company=company,
            location=loc or "Remote",
            url=url,
            description_text=item.get("jobDescription", ""),
            source="jobicy",
            date_posted=item.get("pubDate"),
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.debug("Skipping Jobicy item: %s", e)
        return None


class JobicyClient:
    """Free remote-jobs API; no key required."""

    def __init__(self) -> None:
        """No credentials; client is stateless."""

    async def search(self, preferences: Any) -> list[RawJobPosting]:
        """Search Jobicy for remote jobs matching preferences."""
        params = _build_search_params(preferences)
        if params is None:
            return []
        timeout = aiohttp.ClientTimeout(total=JOB_API_TIMEOUT_SECONDS)
        try:
            # Separate with blocks: combined ones race on aiohttp SSL cleanup
            async with aiohttp.ClientSession(timeout=timeout) as session:  # noqa: SIM117
                async with session.get(JOBICY_BASE_URL, params=params) as response:
                    if response.status != HTTP_OK:
                        logger.debug("Jobicy HTTP %d", response.status)
                        return []
                    data = await response.json(content_type=None)
        except aiohttp.ClientError as e:
            logger.debug("Jobicy connection error: %s", e)
            return []

        if not isinstance(data, dict):
            return []

        results = [
            posting
            for item in data.get("jobs", [])
            if (posting := _parse_jobicy_item(item)) is not None
        ]

        user_location = (
            preferences.location.split(",")[0].strip()
            if getattr(preferences, "location", None)
            else ""
        )
        results = filter_by_location(
            postings=results,
            user_location=user_location,
            remote_ok=bool(getattr(preferences, "remote_ok", False)),
        )

        logger.debug("Jobicy returned %d results", len(results))
        return results
