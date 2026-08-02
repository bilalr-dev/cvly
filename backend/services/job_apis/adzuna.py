"""Adzuna job board API client."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.constants import (
    ADZUNA_RESULTS_PER_PAGE,
    ADZUNA_SEARCH_URL,
    HTTP_OK,
    JOB_API_HTML_FETCH_TIMEOUT_SECONDS,
    JOB_DESC_EXTRACT_MAX_CHARS,
    JOB_DESC_EXTRACT_MIN_CHARS,
)
from backend.utils.dedup import generate_posting_id, is_truncated
from backend.utils.text import unescape_html

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)


class AdzunaClient(BaseJobAPIClient):

    def __init__(self, app_id: str, app_key: str) -> None:
        self.app_id: str = app_id
        self.app_key: str = app_key

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = unescape_html(item.get("title", ""))
        company = unescape_html(item.get("company", {}).get("display_name", ""))
        location = unescape_html(item.get("location", {}).get("display_name", ""))
        id_str = generate_posting_id(title, company, location)

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("redirect_url", ""),
            description_text=unescape_html(item.get("description", "")),
            source="adzuna",
        )

    def _build_search_params(self, preferences: SearchPreferences) -> dict[str, str]:
        """Map preferences to Adzuna query params (what / where / distance km)."""
        params: dict[str, str] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": ADZUNA_RESULTS_PER_PAGE,
            "what": " ".join(preferences.titles),
        }
        if getattr(preferences, "location", None):
            # City only — country suffix confuses Adzuna's where geocoder
            city = preferences.location.split(",")[0].strip()
            params["where"] = city
            radius = int(getattr(preferences, "radius_km", 0) or 0)
            if radius > 0:
                params["distance"] = str(radius)
        return params

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        if not getattr(preferences, "titles", None):
            return []

        try:
            async with aiohttp.ClientSession() as session:
                params = self._build_search_params(preferences)
                logger.debug("Adzuna search params: %s", params)

                async with session.get(ADZUNA_SEARCH_URL, params=params) as response:
                    data = await response.json()

                postings = [self._map_response(item) for item in data.get("results", [])]

                enriched = []
                for posting in postings:
                    if is_truncated(posting.description_text) and posting.url:
                        full_desc = await self._fetch_full_description(posting.url)
                        if full_desc and len(full_desc) > len(posting.description_text):
                            posting = posting.model_copy(update={"description_text": full_desc})
                    enriched.append(posting)

                return enriched

        except aiohttp.ClientError:
            return []

    async def _fetch_full_description(self, url: str) -> str | None:
        """Fetch and extract the full job description from the original posting URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=JOB_API_HTML_FETCH_TIMEOUT_SECONDS),
                    headers={"User-Agent": "Mozilla/5.0 (compatible; Cvly/1.0)"},
                    allow_redirects=True,
                ) as resp:
                    if resp.status != HTTP_OK:
                        return None
                    html = await resp.text()

            clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            clean = unescape_html(clean)
            return clean[:JOB_DESC_EXTRACT_MAX_CHARS] if len(clean) > JOB_DESC_EXTRACT_MIN_CHARS else None
        except (aiohttp.ClientError, OSError):
            return None
