from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"

    # Anthropic
    anthropic_api_key: str = ""

    # Congress.gov
    congress_api_key: str = ""

    # Twitter / X
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_secret: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/agentcongress"

    # App
    dry_run: bool = True
    webapp_url: str = "https://agentcongress.example.com"

    def _get_secret(self, secret_id: str) -> str:
        """Fetch secret from GCP Secret Manager (production only)."""
        from google.cloud import secretmanager  # type: ignore

        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get("GCP_PROJECT_ID", "")
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    def resolve_secrets(self) -> None:
        """In production, pull secrets from GCP Secret Manager."""
        if self.env != "production":
            return
        self.anthropic_api_key = self._get_secret("ANTHROPIC_API_KEY")
        self.congress_api_key = self._get_secret("CONGRESS_API_KEY")
        self.twitter_api_key = self._get_secret("TWITTER_API_KEY")
        self.twitter_api_secret = self._get_secret("TWITTER_API_SECRET")
        self.twitter_access_token = self._get_secret("TWITTER_ACCESS_TOKEN")
        self.twitter_access_secret = self._get_secret("TWITTER_ACCESS_SECRET")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.resolve_secrets()
    return settings
