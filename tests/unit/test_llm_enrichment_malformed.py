"""Regression tests for LLM enrichment resilience to malformed 200 responses."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.core.config import Settings
from autoapply_agent.services import llm_enrichment
from autoapply_agent.services.llm_enrichment import LLMEnrichmentService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


class _FakeResponse:
    """Minimal stand-in for an httpx.Response returning a fixed JSON body."""

    def __init__(self, payload: dict[str, Any]) -> None:
        """Store the JSON payload to return.

        Args:
            payload: Decoded JSON body to return from ``json()``.
        """
        self._payload = payload

    def raise_for_status(self) -> None:
        """No-op: emulate a successful 2xx response."""

    def json(self) -> dict[str, Any]:
        """Return the canned JSON payload."""
        return self._payload


class _FakeAsyncClient:
    """Minimal async context-manager stand-in for httpx.AsyncClient."""

    def __init__(self, payload: dict[str, Any]) -> None:
        """Store the payload to hand back from ``post``.

        Args:
            payload: Decoded JSON body to return from the POST call.
        """
        self._payload = payload

    async def __aenter__(self) -> _FakeAsyncClient:
        """Enter the async context."""
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        """Exit the async context without suppressing exceptions."""
        return False

    async def post(self, *args: Any, **kwargs: Any) -> _FakeResponse:
        """Return a fake successful response with the canned payload."""
        return _FakeResponse(self._payload)


def _candidate() -> JobCandidate:
    """Build a deterministic job candidate for enrichment tests."""
    return JobCandidate(
        external_id="job-1",
        title="ML Engineer",
        location="Remote",
        company="example.ai",
        url="https://example.ai/jobs/1",
        raw=None,
    )


def test_gemini_empty_candidates_returns_none(monkeypatch: MonkeyPatch) -> None:
    """A 200 response with an empty ``candidates`` array must fall back to None."""
    settings = Settings(
        APP_NAME="test",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        LLM_ENABLE_ENRICHMENT=True,
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="dummy-key",
    )
    monkeypatch.setattr(
        llm_enrichment.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient({"candidates": []}),
    )
    service = LLMEnrichmentService(settings)

    result = asyncio.run(
        service.enrich_job_decision(
            job_candidate=_candidate(),
            query="machine learning platform",
            deterministic_rationale=["deterministic baseline"],
        )
    )

    assert result is None


def test_openai_compatible_empty_choices_returns_none(monkeypatch: MonkeyPatch) -> None:
    """A 200 response with an empty ``choices`` array must fall back to None."""
    settings = Settings(
        APP_NAME="test",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        LLM_ENABLE_ENRICHMENT=True,
        LLM_PROVIDER="gpt",
        OPENAI_API_KEY="dummy-key",
    )
    monkeypatch.setattr(
        llm_enrichment.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient({"choices": []}),
    )
    service = LLMEnrichmentService(settings)

    result = asyncio.run(
        service.enrich_job_decision(
            job_candidate=_candidate(),
            query="platform engineering",
            deterministic_rationale=["deterministic baseline"],
        )
    )

    assert result is None
