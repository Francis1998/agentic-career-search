"""Application configuration models."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Agentic Career Search", alias="APP_NAME")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./autoapply_agent.db",
        alias="DATABASE_URL",
    )
    worker_poll_interval_seconds: float = Field(default=0.5, alias="WORKER_POLL_INTERVAL_SECONDS")
    http_timeout_seconds: float = Field(default=12.0, alias="HTTP_TIMEOUT_SECONDS")
    max_jobs_per_source: int = Field(default=50, alias="MAX_JOBS_PER_SOURCE")
    http_user_agent: str = Field(default="agentic-career-search/0.2", alias="HTTP_USER_AGENT")
    enable_worker: bool = Field(default=True, alias="ENABLE_WORKER")
    environment: Literal["dev", "test", "prod"] = Field(default="dev", alias="ENVIRONMENT")


settings = Settings()
