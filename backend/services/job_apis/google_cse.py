"""Google Custom Search job discovery client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.dedup import generate_posting_id

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

class GoogleCSEClient(BaseJobAPIClient):

    def __init__(self, api_key: str, cse_id: str) -> None:
        self.api_key: str = api_key
        self.cse_id: str = cse_id

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = item.get("title", "")
        company = ""
        location = ""
        id_str = generate_posting_id(title, company, location)

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("link", ""),
            source="google_cse",
            description_text=""
        )

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "key": self.api_key,
                    "cx": self.cse_id
                }

                query = " ".join(preferences.titles) if getattr(preferences, "titles", None) else "Developer"
                if getattr(preferences, "location", None):
                    query += f" {preferences.location}"
                params["q"] = query.strip()

                async with session.get(_SEARCH_URL, params=params) as response:
                    data = await response.json()

                return [self._map_response(item) for item in data.get("items", [])]

        except aiohttp.ClientError:
            return []
