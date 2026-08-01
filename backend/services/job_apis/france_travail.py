"""France Travail (Pôle Emploi) job board API client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.services.rate_limiter import AsyncRateLimiter
from backend.utils.constants import (
    CITY_INSEE_CODES,
    FRANCE_TRAVAIL_AUTH_URL,
    FRANCE_TRAVAIL_CONTRACT_CODES,
    FRANCE_TRAVAIL_RATE_LIMIT_CALLS,
    FRANCE_TRAVAIL_RATE_LIMIT_PERIOD_SECONDS,
    FRANCE_TRAVAIL_SEARCH_URL,
    FT_CONTRACT_TYPE_SIGNALS,
    HTTP_OK,
    HTTP_PARTIAL_CONTENT,
    JOB_API_TIMEOUT_SECONDS,
)
from backend.utils.dedup import generate_posting_id

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)


def _contract_type_codes(contracts: list[str]) -> list[str]:
    """Map user contract preferences to France Travail natureOffre codes."""
    codes: set[str] = set()
    for raw in contracts:
        codes.update(FRANCE_TRAVAIL_CONTRACT_CODES.get(str(raw).strip().lower(), []))
    return sorted(codes)


class FranceTravailClient(BaseJobAPIClient):

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.access_token: str | None = None
        # France Travail API: 10 requests/second, 1 000/day
        self._rate_limiter = AsyncRateLimiter(
            max_calls=FRANCE_TRAVAIL_RATE_LIMIT_CALLS,
            period_seconds=FRANCE_TRAVAIL_RATE_LIMIT_PERIOD_SECONDS,
        )

    async def authenticate(self) -> None:
        await self._rate_limiter.acquire()
        timeout = aiohttp.ClientTimeout(total=JOB_API_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(FRANCE_TRAVAIL_AUTH_URL, data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": f"application_{self.client_id} api_offresdemploiv2 o2dsoffre"
                }) as response:
                    data = await response.json(content_type=None)
                    self.access_token = data.get("access_token")
                    if not self.access_token:
                        logger.warning("France Travail auth failed (HTTP %d): %s", response.status, data)
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            logger.warning("France Travail auth error: %s: %s", type(exc).__name__, exc)

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = item.get("intitule", "")
        company = (item.get("entreprise") or {}).get("nom", "")
        location = (item.get("lieuTravail") or {}).get("libelle", "")
        posting_id = generate_posting_id(title, company, location)

        contract_type = None
        if item.get("alternance") is True:
            contract_type = "alternance_apprentissage"
        else:
            raw_contract = item.get("typeContrat", item.get("typeContratLibelle", ""))
            if raw_contract:
                contract_lower = str(raw_contract).lower()
                for ctype, signals in FT_CONTRACT_TYPE_SIGNALS.items():
                    if any(signal in contract_lower for signal in signals):
                        contract_type = ctype
                        break

        return RawJobPosting(
            id=posting_id,
            title=title,
            company=company,
            location=location,
            url=(item.get("origineOffre") or {}).get("urlOrigine", ""),
            description_text=item.get("description", ""),
            source="france_travail",
            contract_type=contract_type,
        )

    def _build_search_params(self, preferences: SearchPreferences) -> dict[str, str]:
        search_keywords = " ".join(preferences.titles)
        params: dict[str, str] = {}

        if getattr(preferences, "location", None):
            city = preferences.location.split(",")[0].strip().lower()
            insee_code = CITY_INSEE_CODES.get(city)
            if insee_code:
                params["commune"] = insee_code
            else:
                search_keywords = f"{search_keywords} {city}".strip()

        if "commune" in params and getattr(preferences, "radius_km", None):
            params["distance"] = str(int(preferences.radius_km))

        contracts = list(getattr(preferences, "contracts", None) or [])
        contract_codes = _contract_type_codes(contracts)
        if contract_codes:
            params["natureOffre"] = ",".join(contract_codes)

        contract_lower = {str(c).lower() for c in contracts}
        has_alternance = any("alternance" in c or "apprentissage" in c for c in contract_lower)
        has_cdd = "cdd" in contract_lower

        # E2 is both CDD and apprenticeship; the alternance flag tells them apart
        if has_cdd and not has_alternance:
            params["alternance"] = "false"
        elif has_alternance:
            params["alternance"] = "true"
            search_keywords = f"{search_keywords} alternance".strip()

        params["motsCles"] = search_keywords
        return params

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        if not getattr(preferences, "titles", None):
            return []

        if not self.access_token:
            await self.authenticate()

        try:
            timeout = aiohttp.ClientTimeout(total=JOB_API_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                params = self._build_search_params(preferences)
                logger.debug("FranceTravail search params: %s", params)

                await self._rate_limiter.acquire()
                async with session.get(
                    FRANCE_TRAVAIL_SEARCH_URL, headers=headers, params=params
                ) as response:
                    if response.status not in (HTTP_OK, HTTP_PARTIAL_CONTENT):
                        body = await response.text()
                        logger.warning(
                            "France Travail search HTTP %d, body: %.500s", response.status, body
                        )
                        return []

                    data = await response.json(content_type=None)
                    if not isinstance(data, dict):
                        logger.warning("France Travail search returned non-dict: %s", type(data))
                        return []

                    return [self._map_response(item) for item in data.get("resultats", [])]

        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            logger.warning("France Travail search error: %s: %s", type(exc).__name__, exc)
            return []
