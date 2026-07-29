from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.dedup import generate_posting_id

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)

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

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-RapidAPI-Key": self.api_key}

                query_parts = []
                if getattr(preferences, "titles", None):
                    query_parts.append(" ".join(preferences.titles))
                if getattr(preferences, "location", None):
                    loc = preferences.location.split(',')[0].strip()
                    query_parts.append(f"in {loc}")

                params = {
                    "query": " ".join(query_parts) if query_parts else "developer",
                    "page": "1",
                    "num_pages": "1"
                }
                logger.debug(f"JSearch params: {params}")

                async with session.get(_SEARCH_URL, headers=headers, params=params) as response:
                    data = await response.json()

                return [self._map_response(item) for item in data.get("data", [])]

        except aiohttp.ClientError:
            return []
