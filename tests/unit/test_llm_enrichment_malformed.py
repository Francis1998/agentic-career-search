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


def test_kimi_empty_choices_returns_none(monkeypatch: MonkeyPatch) -> None:
    """A 200 Kimi response with an empty ``choices`` array must fall back to None."""
    settings = Settings(
        APP_NAME="test",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        LLM_ENABLE_ENRICHMENT=True,
        LLM_PROVIDER="kimi",
        KIMI_API_KEY="dummy-key",
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
            query="agentic recruiting workflow",
            deterministic_rationale=["deterministic baseline"],
        )
    )

    assert result is None


def test_openai_compatible_structured_content_parts_are_joined(monkeypatch: MonkeyPatch) -> None:
    """A 200 response whose ``message.content`` is a content-part list must parse.

    OpenAI-compatible gateways (LiteLLM, vLLM, OpenRouter) may return
    ``choices[0].message.content`` as a list of structured parts, e.g.
    ``[{"type": "text", "text": "Strong fit."}]`` rather than a bare string.
    The normalizer previously only joined list items that were themselves
    strings, so such structured payloads yielded no summary and enrichment was
    silently dropped. The text of each part must be extracted and joined.
    """
    settings = Settings(
        APP_NAME="test",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        LLM_ENABLE_ENRICHMENT=True,
        LLM_PROVIDER="gpt",
        OPENAI_API_KEY="dummy-key",
    )
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "Strong platform fit."},
                        {"type": "text", "text": "Remote friendly."},
                    ]
                }
            }
        ]
    }
    monkeypatch.setattr(
        llm_enrichment.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(payload),
    )
    service = LLMEnrichmentService(settings)

    result = asyncio.run(
        service.enrich_job_decision(
            job_candidate=_candidate(),
            query="platform engineering",
            deterministic_rationale=["deterministic baseline"],
        )
    )

    assert result is not None
    assert result.summary == "Strong platform fit. Remote friendly."


def test_claude_non_object_content_chunks_return_none(monkeypatch: MonkeyPatch) -> None:
    """A 200 Claude response with malformed content chunks must fall back to None."""
    settings = Settings(
        APP_NAME="test",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        LLM_ENABLE_ENRICHMENT=True,
        LLM_PROVIDER="claude",
        CLAUDE_API_KEY="dummy-key",
    )
    monkeypatch.setattr(
        llm_enrichment.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient({"content": [None, "not-a-chunk"]}),
    )
    service = LLMEnrichmentService(settings)

    result = asyncio.run(
        service.enrich_job_decision(
            job_candidate=_candidate(),
            query="agentic career search",
            deterministic_rationale=["deterministic baseline"],
        )
    )

    assert result is None
