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
    EN_FR_TITLE_VARIANTS,
    FRANCE_TRAVAIL_AUTH_URL,
    FRANCE_TRAVAIL_CONTRACT_CODES,
    FRANCE_TRAVAIL_RANGE,
    FRANCE_TRAVAIL_RATE_LIMIT_CALLS,
    FRANCE_TRAVAIL_RATE_LIMIT_PERIOD_SECONDS,
    FRANCE_TRAVAIL_SEARCH_URL,
    FT_CONTRACT_TYPE_SIGNALS,
    HTTP_OK,
    HTTP_PARTIAL_CONTENT,
    JOB_API_TIMEOUT_SECONDS,
    KEYWORD_BOOSTED_CONTRACTS,
)
from backend.utils.dedup import generate_posting_id
from backend.utils.text import unescape_html

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)


def _contract_type_codes(contracts: list[str]) -> list[str]:
    """Map user contract preferences to France Travail natureOffre codes."""
    codes: set[str] = set()
    for raw in contracts:
        codes.update(FRANCE_TRAVAIL_CONTRACT_CODES.get(str(raw).strip().lower(), []))
    return sorted(codes)


def _apply_contract_keyword_boosts(keywords: str, contracts: list[str]) -> str:
    """Append contract keywords that have no natureOffre code (e.g. stage)."""
    result = keywords
    contract_lower = {str(c).lower() for c in contracts}
    if any("alternance" in c or "apprentissage" in c for c in contract_lower):
        if "alternance" not in result.lower():
            result = f"{result} alternance".strip()
    for contract in (str(c).lower() for c in contracts):
        boost_keywords = KEYWORD_BOOSTED_CONTRACTS.get(contract, [])
        if boost_keywords and boost_keywords[0] not in result.lower():
            result = f"{result} {boost_keywords[0]}".strip()
    return result


def _mots_cles_queries(preferences: SearchPreferences) -> list[str]:
    """Build one or two motsCles strings (EN + optional FR) without AND-merging them."""
    contracts = list(getattr(preferences, "contracts", None) or [])
    titles = list(getattr(preferences, "titles", None) or [])
    english = _apply_contract_keyword_boosts(" ".join(titles), contracts)
    queries = [english]

    titles_key = " ".join(titles).lower().strip()
    french_title = EN_FR_TITLE_VARIANTS.get(titles_key)
    if french_title:
        french = _apply_contract_keyword_boosts(french_title, contracts)
        if french.lower() != english.lower():
            queries.append(french)
    return queries


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
        title = unescape_html(item.get("intitule", ""))
        company = unescape_html((item.get("entreprise") or {}).get("nom", ""))
        location = unescape_html((item.get("lieuTravail") or {}).get("libelle", ""))
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
            description_text=unescape_html(item.get("description", "")),
            source="france_travail",
            contract_type=contract_type,
        )

    def _build_search_params(
        self,
        preferences: SearchPreferences,
        mots_cles: str,
    ) -> dict[str, str]:
        params: dict[str, str] = {
            "motsCles": mots_cles,
            "range": FRANCE_TRAVAIL_RANGE,
        }

        if getattr(preferences, "location", None):
            city = preferences.location.split(",")[0].strip().lower()
            insee_code = CITY_INSEE_CODES.get(city)
            if insee_code:
                params["commune"] = insee_code
            elif city and city not in mots_cles.lower():
                params["motsCles"] = f"{mots_cles} {city}".strip()

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

        return params

    async def _fetch_page(
        self,
        session: aiohttp.ClientSession,
        headers: dict[str, str],
        params: dict[str, str],
    ) -> list[RawJobPosting]:
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

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        if not getattr(preferences, "titles", None):
            return []

        if not self.access_token:
            await self.authenticate()

        try:
            timeout = aiohttp.ClientTimeout(total=JOB_API_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                merged: list[RawJobPosting] = []
                seen: set[str] = set()

                for mots_cles in _mots_cles_queries(preferences):
                    params = self._build_search_params(preferences, mots_cles)
                    logger.debug("FranceTravail search params: %s", params)
                    for posting in await self._fetch_page(session, headers, params):
                        if posting.id not in seen:
                            seen.add(posting.id)
                            merged.append(posting)

                return merged

        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            logger.warning("France Travail search error: %s: %s", type(exc).__name__, exc)
            return []
