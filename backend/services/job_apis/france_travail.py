from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.dedup import generate_posting_id

from .base import BaseJobAPIClient
from backend.services.rate_limiter import AsyncRateLimiter
from backend.utils.constants import CITY_INSEE_CODES

logger = logging.getLogger(__name__)

_AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


class FranceTravailClient(BaseJobAPIClient):

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.access_token: str | None = None
        # France Travail API: 10 requests/second, 1 000/day
        self._rate_limiter = AsyncRateLimiter(max_calls=9, period_seconds=1.0)

    async def authenticate(self) -> None:
        await self._rate_limiter.acquire()
        timeout = aiohttp.ClientTimeout(total=15)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(_AUTH_URL, data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": f"application_{self.client_id} api_offresdemploiv2 o2dsoffre"
                }) as response:
                    data = await response.json(content_type=None)
                    self.access_token = data.get("access_token")
                    if not self.access_token:
                        logger.warning("France Travail auth failed — HTTP %d — response: %s", response.status, data)
        except aiohttp.ClientError as exc:
            logger.warning("France Travail auth connection error: %s: %s", type(exc).__name__, exc)
        except Exception as exc:
            logger.warning("France Travail auth unexpected error: %s: %s", type(exc).__name__, exc)

    def _map_response(self, item: dict[str, Any]) -> RawJobPosting:
        title = item.get("intitule", "")
        company = item.get("entreprise", {}).get("nom", "")
        location = item.get("lieuTravail", {}).get("libelle", "")
        id_str = generate_posting_id(title, company, location)

        raw_contract = item.get("typeContrat", item.get("typeContratLibelle", ""))
        contract_type = None
        if raw_contract:
            ct_lower = raw_contract.lower()
            if "cdi" in ct_lower:
                contract_type = "CDI"
            elif "cdd" in ct_lower:
                contract_type = "CDD"
            elif "stage" in ct_lower:
                contract_type = "stage"
            elif "alternance" in ct_lower or "apprentissage" in ct_lower:
                contract_type = "alternance_apprentissage"
            elif "freelance" in ct_lower:
                contract_type = "freelance"

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("origineOffre", {}).get("urlOrigine", ""),
            description_text=item.get("description", ""),
            source="france_travail",
            contract_type=contract_type
        )

    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        if not self.access_token:
            await self.authenticate()

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                params: dict[str, str] = {}

                if getattr(preferences, "titles", None):
                    params["motsCles"] = " ".join(preferences.titles)

                if getattr(preferences, "location", None):
                    city = preferences.location.split(",")[0].strip().lower()
                    insee_code = CITY_INSEE_CODES.get(city)
                    if insee_code:
                        # Use INSEE commune code so distance filtering is respected
                        params["commune"] = insee_code
                    else:
                        # Fallback: append city name to keyword search (distance ignored)
                        params["motsCles"] = f"{params.get('motsCles', '')} {city}".strip()

                if getattr(preferences, "radius_km", None):
                    params["distance"] = str(int(preferences.radius_km))

                logger.debug("FranceTravail search params: %s", params)

                await self._rate_limiter.acquire()
                async with session.get(_SEARCH_URL, headers=headers, params=params) as response:
                    if response.status not in (200, 206):
                        body = await response.text()
                        logger.warning(
                            "France Travail search HTTP %d — body: %.500s", response.status, body
                        )
                        return []

                    data = await response.json(content_type=None)
                    if not isinstance(data, dict):
                        logger.warning("France Travail search returned non-dict: %s", type(data))
                        return []

                    return [self._map_response(item) for item in data.get("resultats", [])]

        except aiohttp.ClientError as exc:
            logger.warning("France Travail search error: %s: %s", type(exc).__name__, exc)
            return []
        except Exception as exc:
            logger.warning("France Travail search unexpected error: %s: %s", type(exc).__name__, exc)
            return []
