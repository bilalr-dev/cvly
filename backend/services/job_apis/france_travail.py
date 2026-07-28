from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences
from backend.utils.dedup import generate_posting_id

from .base import BaseJobAPIClient

logger = logging.getLogger(__name__)

_AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

class FranceTravailClient(BaseJobAPIClient):

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.access_token: str | None = None

    async def authenticate(self) -> None:
        async with aiohttp.ClientSession() as session, session.post(_AUTH_URL, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre"
        }) as response:
            data = await response.json()
            self.access_token = data.get("access_token")

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
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                params: dict[str, str] = {}

                if getattr(preferences, "titles", None):
                    mots_cles = ",".join(preferences.titles)
                else:
                    mots_cles = ""

                if getattr(preferences, "location", None):
                    mots_cles = f"{mots_cles},{preferences.location}" if mots_cles else preferences.location

                if mots_cles:
                    params["motsCles"] = mots_cles

                if getattr(preferences, "radius_km", None):
                    params["distance"] = str(preferences.radius_km)

                logger.info(f"FranceTravail search params: {params}")

                async with session.get(_SEARCH_URL, headers=headers, params=params) as response:
                    data = await response.json()

                return [self._map_response(item) for item in data.get("resultats", [])]

        except aiohttp.ClientError:
            return []
