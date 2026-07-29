from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.dedup import generate_posting_id, is_truncated

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/fr/search/1"

class AdzunaClient(BaseJobAPIClient):

    def __init__(self, app_id: str, app_key: str) -> None:
        self.app_id: str = app_id
        self.app_key: str = app_key

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = item.get("title", "")
        company = item.get("company", {}).get("display_name", "")
        location = item.get("location", {}).get("display_name", "")
        id_str = generate_posting_id(title, company, location)

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("redirect_url", ""),
            description_text=item.get("description", ""),
            source="adzuna"
        )

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                    "results_per_page": "20",
                }

                if getattr(preferences, "titles", None):
                    params["what"] = " ".join(preferences.titles)
                if getattr(preferences, "location", None):
                    params["where"] = preferences.location

                logger.debug(f"Adzuna search params: {params}")

                async with session.get(_SEARCH_URL, params=params) as response:
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
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"User-Agent": "Mozilla/5.0 (compatible; Cvly/1.0)"},
                    allow_redirects=True,
                ) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()

            # parsing standard JD payload structures
            # Remove script, style, nav, header, footer tags
            # Extract visible text from main content area
            import re
            # Remove HTML tags
            clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
            clean = re.sub(r'<[^>]+>', ' ', clean)
            # Normalize whitespace
            clean = re.sub(r'\s+', ' ', clean).strip()
            # Return first 3000 chars of extracted text (enough for JD parsing)
            return clean[:3000] if len(clean) > 200 else None
        except Exception:
            return None
