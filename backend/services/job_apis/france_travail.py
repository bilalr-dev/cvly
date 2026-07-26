from __future__ import annotations

import aiohttp
from typing import List, Any

from .base import BaseJobAPIClient
from backend.models.preferences import SearchPreferences
from backend.models.job import RawJobPosting
from backend.utils.dedup import generate_posting_id

_AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

class FranceTravailClient(BaseJobAPIClient):

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.access_token: str | None = None

    async def authenticate(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.post(_AUTH_URL, data={
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

        return RawJobPosting(
            id=id_str,
            title=title,
            company=company,
            location=location,
            url=item.get("origineOffre", {}).get("urlOrigine", ""),
            description_text=item.get("description", ""),
            source="france_travail"
        )

    async def search(self, preferences: SearchPreferences) -> List[RawJobPosting]:
        if not self.access_token:
            await self.authenticate()

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                params: dict[str, str] = {}

                if getattr(preferences, "keywords", None):
                    params["motsCles"] = ",".join(preferences.keywords)
                if getattr(preferences, "locations", None):
                    params["commune"] = ",".join(preferences.locations)
                if getattr(preferences, "radius_km", None):
                    params["distance"] = str(preferences.radius_km)

                async with session.get(_SEARCH_URL, headers=headers, params=params) as response:
                    data = await response.json()

                return [self._map_response(item) for item in data.get("resultats", [])]

        except aiohttp.ClientError:
            return []
