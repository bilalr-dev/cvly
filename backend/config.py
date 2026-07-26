from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    gemini_api_key: str

    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None

    france_travail_client_id: str | None = None
    france_travail_client_secret: str | None = None

    google_cse_api_key: str | None = None
    google_cse_id: str | None = None

    google_sheet_id: str | None = None

    jsearch_api_key: str | None = None

    app_port: int = 8000
    default_country: str = "FR"
    default_language: str = "fr"
    google_service_account_path: str = "config/google_service_account.json"
    match_threshold: int = 50

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
