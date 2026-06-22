"""Unit tests for optional LLM enrichment service."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.core.config import Settings
from autoapply_agent.services.llm_enrichment import LLMEnrichmentService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_enrichment_returns_none_when_provider_key_missing() -> None:
    """Service returns no enrichment when configured key is absent."""

    settings = Settings(
        APP_NAME="test",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        LLM_ENABLE_ENRICHMENT=True,
        LLM_PROVIDER="gemini",
    )
    service = LLMEnrichmentService(settings)
    candidate = JobCandidate(
        external_id="job-1",
        title="ML Engineer",
        location="Remote",
        company="example.ai",
        url="https://example.ai/jobs/1",
        raw=None,
    )

    enrichment = asyncio.run(
        service.enrich_job_decision(
            job_candidate=candidate,
            query="machine learning platform",
            deterministic_rationale=["deterministic baseline"],
        )
    )
    assert enrichment is None


def test_enrichment_returns_none_when_gpt_key_missing() -> None:
    """Service returns no enrichment when GPT key is absent."""

    settings = Settings(
        APP_NAME="test",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        LLM_ENABLE_ENRICHMENT=True,
        LLM_PROVIDER="gpt",
    )
    service = LLMEnrichmentService(settings)
    candidate = JobCandidate(
        external_id="job-2",
        title="Platform Engineer",
        location="Remote",
        company="example.ai",
        url="https://example.ai/jobs/2",
        raw=None,
    )

    enrichment = asyncio.run(
        service.enrich_job_decision(
            job_candidate=candidate,
            query="platform engineering",
            deterministic_rationale=["deterministic baseline"],
        )
    )
    assert enrichment is None


def test_settings_default_gpt_model_uses_latest_stack() -> None:
    """Default GPT-compatible model tracks the current agentic stack."""

    settings = Settings(APP_NAME="test", DATABASE_URL="sqlite+aiosqlite:///./test.db")

    assert settings.openai_model == "gpt-5.5"


def test_normalize_text_handles_string_and_list() -> None:
    """Normalize text helper handles both direct and segmented content."""

    assert LLMEnrichmentService._normalize_text("  hello  ") == "hello"
    assert LLMEnrichmentService._normalize_text(["a", " ", "b"]) == "a b"
    assert LLMEnrichmentService._normalize_text([]) is None
