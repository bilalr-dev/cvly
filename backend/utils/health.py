"""API health check"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import aiohttp

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class APIStatus:
    name: str
    configured: bool
    connected: bool
    error: str = ""


async def _test_url(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 5,
) -> tuple[bool, str]:
    """Test if a URL is reachable."""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.get(url, headers=headers or {}) as resp:
                return resp.status < 400, ""
    except Exception as e:
        return False, str(e)


async def check_all_apis() -> list[APIStatus]:
    """Check connectivity for all configured APIs."""
    settings = get_settings()
    results: list[APIStatus] = []

    # Gemini
    key = settings.gemini_api_key
    if key:
        ok, err = await _test_url(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        )
        results.append(APIStatus("Gemini", True, ok, err))
    else:
        results.append(APIStatus("Gemini", False, False))

    # Groq
    key = settings.groq_api_key
    if key:
        ok, err = await _test_url(
            "https://api.groq.com/openai/v1/models",
            {"Authorization": f"Bearer {key}"},
        )
        results.append(APIStatus("Groq", True, ok, err))
    else:
        results.append(APIStatus("Groq", False, False))

    # France Travail
    if settings.france_travail_client_id and settings.france_travail_client_secret:
        results.append(APIStatus("France Travail", True, True))
    else:
        results.append(APIStatus("France Travail", False, False))

    # Adzuna
    if settings.adzuna_app_id and settings.adzuna_app_key:
        results.append(APIStatus("Adzuna", True, True))
    else:
        results.append(APIStatus("Adzuna", False, False))

    results.append(APIStatus("Arbeitnow", True, True))
    results.append(APIStatus("Remotive", True, True))
    results.append(APIStatus("Jobicy", True, True))

    # JSearch
    if settings.jsearch_api_key:
        results.append(APIStatus("JSearch", True, True))
    else:
        results.append(APIStatus("JSearch", False, False))

    # La Bonne Alternance
    if settings.la_bonne_alternance_api_key:
        results.append(APIStatus("La Bonne Alternance", True, True))
    else:
        results.append(APIStatus("La Bonne Alternance", False, False))

    # Google Sheets
    if settings.google_sheet_id and settings.google_service_account_path:
        results.append(APIStatus("Google Sheets", True, True))
    else:
        results.append(APIStatus("Google Sheets", False, False))

    return results
