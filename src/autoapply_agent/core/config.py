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
    llm_enable_enrichment: bool = Field(default=False, alias="LLM_ENABLE_ENRICHMENT")
    llm_provider: Literal["gemini", "kimi", "claude", "gpt"] = Field(
        default="gemini",
        alias="LLM_PROVIDER",
    )
    llm_timeout_seconds: float = Field(default=12.0, alias="LLM_TIMEOUT_SECONDS")

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    kimi_api_key: str | None = Field(default=None, alias="KIMI_API_KEY")
    kimi_model: str = Field(default="moonshot-v1-8k", alias="KIMI_MODEL")
    kimi_base_url: str = Field(default="https://api.moonshot.cn/v1", alias="KIMI_BASE_URL")

    claude_api_key: str | None = Field(default=None, alias="CLAUDE_API_KEY")
    claude_model: str = Field(default="claude-3-5-sonnet-latest", alias="CLAUDE_MODEL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")


settings = Settings()
