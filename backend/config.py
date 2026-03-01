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

    # Scheduler: set disable_scheduler=true when using Cloud Scheduler (or other external cron)
    # to trigger POST /admin/trigger-poll. When set, scheduler_secret can be used to protect that endpoint.
    disable_scheduler: bool = False
    scheduler_secret: str = ""

    # Cloud Tasks (optional): when set, POST /admin/schedule-poll enqueues work to Cloud Tasks
    # so each debate runs in a separate task (shorter requests, retries per debate).
    service_url: str = ""  # e.g. https://your-backend.run.app
    cloud_tasks_project_id: str = ""
    cloud_tasks_location: str = ""
    cloud_tasks_queue_name: str = ""

    def _get_secret(self, secret_id: str, project_id: str) -> str:
        """Fetch secret from GCP Secret Manager (production only)."""
        from google.cloud import secretmanager  # type: ignore

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    def resolve_secrets(self) -> None:
        """In production, pull secrets from GCP Secret Manager."""
        if self.env != "production":
            return
        project_id = (os.environ.get("GCP_PROJECT_ID") or "").strip()
        if not project_id:
            raise ValueError(
                "GCP_PROJECT_ID must be set when ENV=production (e.g. in .env.production or Cloud Run env). "
                "Set it to your GCP project ID (e.g. agentcongress)."
            )
        self.anthropic_api_key = self._get_secret("ANTHROPIC_API_KEY", project_id)
        self.congress_api_key = self._get_secret("CONGRESS_API_KEY", project_id)
        self.twitter_api_key = self._get_secret("TWITTER_API_KEY", project_id)
        self.twitter_api_secret = self._get_secret("TWITTER_API_SECRET", project_id)
        self.twitter_access_token = self._get_secret("TWITTER_ACCESS_TOKEN", project_id)
        self.twitter_access_secret = self._get_secret("TWITTER_ACCESS_SECRET", project_id)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.resolve_secrets()
    return settings
