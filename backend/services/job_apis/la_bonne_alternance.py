"""La Bonne Alternance job API client (free with API key).

API docs: https://api.apprentissage.beta.gouv.fr/fr/explorer/recherche-offre
Endpoint: https://api.apprentissage.beta.gouv.fr/api/job/v1/search
Auth: free API token from the developer portal.
Only queried when the user selected alternance or stage contracts.
ROME codes come from SearchPreferences.rome_codes (resolved via Gemini in the pipeline).
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.constants import (
    CITY_COORDINATES,
    HTTP_OK,
    JOB_API_TIMEOUT_SECONDS,
    LBA_BASE_URL,
    LBA_DEFAULT_RADIUS_KM,
    LBA_MAX_RADIUS_KM,
    LBA_SOURCES,
)
from backend.utils.dedup import generate_posting_id

logger = logging.getLogger(__name__)


def _wants_niche_contracts(preferences: SearchPreferences) -> bool:
    contracts = list(getattr(preferences, "contracts", None) or [])
    if not contracts:
        return False
    contract_lower = {str(c).lower() for c in contracts}
    return any(
        "alternance" in c or "apprentissage" in c or "stage" in c
        for c in contract_lower
    )


def _search_radius_km(preferences: SearchPreferences) -> int:
    raw = int(getattr(preferences, "radius_km", 0) or LBA_DEFAULT_RADIUS_KM)
    return min(max(raw, 1), LBA_MAX_RADIUS_KM)


def _joined_api_types(item: dict[str, Any]) -> str:
    """Return a joined lowercase string of the API contract type labels."""
    types = (item.get("contract") or {}).get("type") or []
    if isinstance(types, str):
        types = [types]
    return " ".join(str(t).lower() for t in types)


def _contract_type_from_api_label(joined: str) -> str | None:
    """Resolve a contract type from the API-supplied label, or return None."""
    if "professionnalisation" in joined:
        return "alternance_professionnalisation"
    if "apprentissage" in joined or "alternance" in joined:
        return "alternance_apprentissage"
    if "stage" in joined or "internship" in joined:
        return "stage"
    return None


def _contract_type_from_preferences(contracts: set[str]) -> str:
    """Fall back to the user's selected contract type when the API provides none."""
    if any("professionnalisation" in c for c in contracts):
        return "alternance_professionnalisation"
    wants_stage = any("stage" in c for c in contracts)
    wants_alt = any("alternance" in c or "apprentissage" in c for c in contracts)
    if wants_stage and not wants_alt:
        return "stage"
    return "alternance_apprentissage"


def _contract_type_for_item(item: dict[str, Any], preferences: SearchPreferences) -> str:
    """Prefer API contract labels; fall back to the user's selected niche type."""
    api_type = _contract_type_from_api_label(_joined_api_types(item))
    if api_type:
        return api_type
    contracts = {str(c).lower() for c in (getattr(preferences, "contracts", None) or [])}
    return _contract_type_from_preferences(contracts)


def _parse_lba_item(
    item: dict[str, Any],
    fallback_city: str,
    preferences: SearchPreferences,
) -> RawJobPosting | None:
    try:
        offer = item.get("offer") or {}
        workplace = item.get("workplace") or {}
        apply_info = item.get("apply") or {}
        location_info = workplace.get("location") or {}

        title = offer.get("title") or ""
        company = workplace.get("brand") or workplace.get("name") or ""
        location = location_info.get("address") or fallback_city
        url = apply_info.get("url") or ""
        description = offer.get("description") or ""
        posting_id = generate_posting_id(title, company, location)

        return RawJobPosting(
            id=posting_id,
            title=title,
            company=company,
            location=location,
            url=url,
            description_text=description,
            source="la_bonne_alternance",
            contract_type=_contract_type_for_item(item, preferences),
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.debug("Skipping LBA item: %s", e)
        return None


def _item_matches_diploma(item: dict[str, Any], diploma_level: int | None) -> bool:
    """Keep offers at or above the candidate diploma; unknowns pass (API already filtered)."""
    if not diploma_level:
        return True
    offer = item.get("offer") or {}
    target = offer.get("target_diploma") or {}
    european = target.get("european")
    if european in (None, ""):
        return True
    try:
        return int(european) >= int(diploma_level)
    except (TypeError, ValueError):
        return True


class LaBonneAlternanceClient:
    """Free alternance/stage job board (API key required, free signup)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _build_search_params(self, preferences: SearchPreferences) -> dict[str, str] | None:
        rome_codes = [
            str(code).strip().upper()
            for code in (getattr(preferences, "rome_codes", None) or [])
            if str(code).strip()
        ][:5]
        if not rome_codes:
            return None

        city = ""
        if getattr(preferences, "location", None):
            city = preferences.location.split(",")[0].strip().lower()
        coords = CITY_COORDINATES.get(city)
        if not coords:
            return None

        lat, lon = coords
        params = {
            "romes": ",".join(rome_codes),
            "latitude": str(lat),
            "longitude": str(lon),
            "radius": str(_search_radius_km(preferences)),
            "sources": LBA_SOURCES,
        }
        diploma_level = getattr(preferences, "diploma_level", None)
        if diploma_level:
            params["target_diploma_level"] = str(diploma_level)
        return params

    async def _fetch_lba_data(
        self,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> dict | None:
        """Perform the HTTP request and return parsed JSON, or None on failure."""
        timeout = aiohttp.ClientTimeout(total=JOB_API_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:  # noqa: SIM117
                async with session.get(LBA_BASE_URL, params=params, headers=headers) as response:
                    if response.status != HTTP_OK:
                        body = await response.text()
                        logger.warning("La Bonne Alternance HTTP %d: %.300s", response.status, body)
                        return None
                    return await response.json(content_type=None)
        except aiohttp.ClientError as e:
            logger.warning("La Bonne Alternance connection error: %s", e)
            return None

    def _collect_postings(
        self,
        data: dict,
        preferences: SearchPreferences,
        fallback_city: str,
        limit: int,
        diploma_level: int | None,
    ) -> list[RawJobPosting]:
        """Parse raw API items into RawJobPosting objects up to the given limit."""
        results: list[RawJobPosting] = []
        for item in data.get("jobs") or []:
            if not isinstance(item, dict):
                continue
            if not _item_matches_diploma(item, diploma_level):
                continue
            posting = _parse_lba_item(item, fallback_city, preferences)
            if posting is not None:
                results.append(posting)
            if len(results) >= limit:
                break
        return results

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        """Search La Bonne Alternance using the user's location, radius, and titles."""
        if not _wants_niche_contracts(preferences):
            return []
        if not getattr(preferences, "titles", None):
            return []

        params = self._build_search_params(preferences)
        if params is None:
            return []

        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = await self._fetch_lba_data(params, headers)
        if not isinstance(data, dict):
            return []

        city = preferences.location.split(",")[0].strip() if preferences.location else ""
        fallback_city = city.title() if city else ""
        limit = int(getattr(preferences, "max_results_per_source", 0) or 20)
        diploma_level = getattr(preferences, "diploma_level", None)

        results = self._collect_postings(data, preferences, fallback_city, limit, diploma_level)
        logger.debug("LBA returned %d alternance jobs (limit=%d)", len(results), limit)
        return results
