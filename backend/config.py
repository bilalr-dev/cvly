from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    # Gemini
    gemini_api_key: str

    # Adzuna
    adzuna_app_id: Optional[str] = None
    adzuna_app_key: Optional[str] = None

    # France Travail
    france_travail_client_id: Optional[str] = None
    france_travail_client_secret: Optional[str] = None

    # Google CSE
    google_cse_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None

    # Google Sheets
    google_sheet_id: Optional[str] = None

    # JSearch
    jsearch_api_key: Optional[str] = None

    # App config
    app_port: int = 8000
    default_country: str = "FR"
    default_language: str = "fr"
    google_service_account_path: str = "config/google_service_account.json"
    match_threshold: int = 50

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
