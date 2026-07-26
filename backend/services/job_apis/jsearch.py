from __future__ import annotations

import aiohttp
from typing import List, Any

from .base import BaseJobAPIClient
from backend.models.preferences import SearchPreferences
from backend.models.job import RawJobPosting
from backend.utils.dedup import generate_posting_id

_SEARCH_URL = "https://jsearch.p.rapidapi.com/search"

class JSearchClient(BaseJobAPIClient):

    def __init__(self, api_key: str) -> None:
        self.api_key: str = api_key

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = item.get("job_title", "")
        company = item.get("employer_name", "")
        location = item.get("job_city", "")
        id_str = generate_posting_id(title, company, location)

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("job_apply_link", ""),
            source="jsearch",
            description_text=""
        )

    async def search(self, preferences: SearchPreferences) -> List[RawJobPosting]:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-RapidAPI-Key": self.api_key}

                async with session.get(_SEARCH_URL, headers=headers, params={}) as response:
                    data = await response.json()

                return [self._map_response(item) for item in data.get("data", [])]

        except aiohttp.ClientError:
            return []
