from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.constants import JSEARCH_DEFAULT_PARAMS
from backend.utils.dedup import generate_posting_id

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://jsearch.p.rapidapi.com/search-v2"

class JSearchClient(BaseJobAPIClient):

    def __init__(self, api_key: str) -> None:
        self.api_key: str = api_key

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = item.get("job_title") or ""
        company = item.get("employer_name") or ""
        location = item.get("job_city") or ""
        id_str = generate_posting_id(title, company, location)

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("job_apply_link") or "",
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
                    **JSEARCH_DEFAULT_PARAMS,
                    "query": " ".join(query_parts) if query_parts else "developer",
                }
                country = getattr(preferences, "country", "FR").lower()
                params["country"] = country
                logger.debug("JSearch params: %s", params)

                async with session.get(_SEARCH_URL, headers=headers, params=params) as response:
                    data = await response.json()

                # v1 format (old): data.get("data", [])
                # v2 format (new): data.get("data", {}).get("jobs", [])
                payload = data.get("data", {})
                if isinstance(payload, dict):
                    items = payload.get("jobs", [])
                elif isinstance(payload, list):
                    items = payload
                else:
                    items = []

                return [self._map_response(item) for item in items]

        except aiohttp.ClientError:
            return []
