"""Application settings loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    gemini_api_key: str

    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None

    france_travail_client_id: str | None = None
    france_travail_client_secret: str | None = None

    google_sheet_id: str | None = None

    groq_api_key: str | None = None

    jsearch_api_key: str | None = None

    app_port: int = 8000
    default_country: str = "FR"
    default_language: str = "fr"
    google_service_account_path: str = "config/google_service_account.json"
    match_threshold: int = 50
    max_jd_parse: int = 40

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return a cached singleton AppSettings instance (reads .env once)."""
    return AppSettings()  # pyright: ignore[reportCallIssue]
