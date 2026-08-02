"""JSearch (RapidAPI) job board client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.config import get_settings
from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.constants import JSEARCH_DEFAULT_PARAMS
from backend.utils.dedup import generate_posting_id
from backend.utils.text import unescape_html

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://jsearch.p.rapidapi.com/search-v2"


class JSearchClient(BaseJobAPIClient):

    def __init__(self, api_key: str) -> None:
        self.api_key: str = api_key

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = unescape_html(item.get("job_title") or "")
        company = unescape_html(item.get("employer_name") or "")
        location = unescape_html(item.get("job_city") or "")
        id_str = generate_posting_id(title, company, location)
        description = unescape_html(
            item.get("job_description")
            or item.get("job_description_snippet")
            or ""
        )

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("job_apply_link") or "",
            source="jsearch",
            description_text=description,
        )

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        titles = getattr(preferences, "titles", None) or []
        if not titles:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-RapidAPI-Key": self.api_key}

                # Docs: put title + location in the free-form query string
                query_parts = [" ".join(titles)]
                if getattr(preferences, "location", None):
                    loc = preferences.location.split(",")[0].strip()
                    query_parts.append(f"in {loc}")

                params = {
                    **JSEARCH_DEFAULT_PARAMS,
                    "query": " ".join(query_parts),
                }
                country = (
                    getattr(preferences, "country", None) or get_settings().default_country
                ).lower()
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
