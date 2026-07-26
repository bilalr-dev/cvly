from __future__ import annotations

import aiohttp
from typing import List, Any

from .base import BaseJobAPIClient
from backend.models.preferences import SearchPreferences
from backend.models.job import RawJobPosting
from backend.utils.dedup import generate_posting_id

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

    async def search(self, preferences: SearchPreferences) -> List[RawJobPosting]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                }

                if getattr(preferences, "keywords", None):
                    params["what"] = " ".join(preferences.keywords)
                if getattr(preferences, "locations", None):
                    params["where"] = " ".join(preferences.locations)

                async with session.get(_SEARCH_URL, params=params) as response:
                    data = await response.json()

                return [self._map_response(item) for item in data.get("results", [])]

        except aiohttp.ClientError:
            return []
