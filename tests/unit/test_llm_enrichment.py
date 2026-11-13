"""Unit tests for optional LLM enrichment service."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import httpx
import pytest

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


def test_settings_defaults_use_the_current_model_stack() -> None:
    """Default models track the verified current provider line-ups (2026-11)."""

    settings = Settings(APP_NAME="test", DATABASE_URL="sqlite+aiosqlite:///./test.db")

    assert settings.openai_model == "gpt-6-luna"
    assert settings.openai_reasoning_effort == "none"
    assert settings.claude_model == "claude-haiku-5-5"
    assert settings.claude_effort == "low"
    assert settings.gemini_model == "gemini-3.8-flash"
    assert settings.kimi_model == "kimi-k3.1-pro"
    assert settings.kimi_base_url == "https://api.moonshot.ai/v1"


def test_normalize_text_handles_string_and_list() -> None:
    """Normalize text helper handles both direct and segmented content."""

    assert LLMEnrichmentService._normalize_text("  hello  ") == "hello"
    assert LLMEnrichmentService._normalize_text(["a", " ", "b"]) == "a b"
    assert LLMEnrichmentService._normalize_text([]) is None


def _capture_requests(
    monkeypatch: MonkeyPatch, reply: dict[str, object]
) -> list[dict[str, object]]:
    """Route provider HTTP calls to an in-memory transport and record JSON bodies.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        reply: JSON body every provider call answers with.

    Returns:
        List that receives each request's decoded JSON payload.
    """

    captured: list[dict[str, object]] = []
    real_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=reply)

    def client_factory(**kwargs: object) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(llm_enrichment.httpx, "AsyncClient", client_factory)
    return captured


def _enrich(settings: Settings) -> llm_enrichment.LLMEnrichmentResult | None:
    """Run one enrichment call for a fixed candidate."""

    candidate = JobCandidate(
        external_id="job-3",
        title="Staff Backend Engineer",
        location="Remote - US",
        company="example.ai",
        url="https://example.ai/jobs/3",
        raw=None,
    )
    return asyncio.run(
        LLMEnrichmentService(settings).enrich_job_decision(
            job_candidate=candidate,
            query="python backend",
            deterministic_rationale=["deterministic baseline"],
        )
    )


_OPENAI_REPLY: dict[str, object] = {
    "choices": [{"message": {"content": "Strong fit.", "reasoning_content": "hidden"}}]
}


def test_kimi_k3_requests_omit_fixed_sampling_parameters(monkeypatch: MonkeyPatch) -> None:
    """K3-series Kimi models reject any temperature but 1.0: never send sampling params."""

    captured = _capture_requests(monkeypatch, _OPENAI_REPLY)
    settings = Settings(LLM_PROVIDER="kimi", KIMI_API_KEY="test-key", KIMI_MODEL="kimi-k3.1-pro")

    result = _enrich(settings)

    assert result is not None and result.summary == "Strong fit."
    payload = captured[0]
    assert {"temperature", "top_p", "n", "presence_penalty", "frequency_penalty"}.isdisjoint(
        payload
    )
    assert payload["reasoning_effort"] == "low"
    assert payload["max_completion_tokens"] >= 1024


def test_kimi_k2_requests_omit_temperature_without_reasoning_effort(
    monkeypatch: MonkeyPatch,
) -> None:
    """Retiring K2 models also fix temperature and do not accept ``reasoning_effort``."""

    captured = _capture_requests(monkeypatch, _OPENAI_REPLY)

    _enrich(Settings(LLM_PROVIDER="kimi", KIMI_API_KEY="test-key", KIMI_MODEL="kimi-k2.6"))

    assert "temperature" not in captured[0]
    assert "reasoning_effort" not in captured[0]


def test_gpt_6_requests_use_reasoning_effort_and_completion_token_budget(
    monkeypatch: MonkeyPatch,
) -> None:
    """GPT-6 Luna runs without reasoning (temperature allowed); other efforts drop it."""

    captured = _capture_requests(monkeypatch, _OPENAI_REPLY)

    _enrich(Settings(LLM_PROVIDER="gpt", OPENAI_API_KEY="test-key"))
    _enrich(
        Settings(
            LLM_PROVIDER="gpt",
            OPENAI_API_KEY="test-key",
            OPENAI_MODEL="gpt-6.1-sol",
            OPENAI_REASONING_EFFORT="low",
        )
    )
    _enrich(Settings(LLM_PROVIDER="gpt", OPENAI_API_KEY="test-key", OPENAI_REASONING_EFFORT=""))

    luna, sol, unset = captured
    assert luna["model"] == "gpt-6-luna"
    assert luna["reasoning_effort"] == "none"
    assert luna["temperature"] == 0.2
    assert sol["reasoning_effort"] == "low"
    assert "temperature" not in sol
    assert "reasoning_effort" not in unset and "temperature" not in unset
    for payload in captured:
        assert "max_tokens" not in payload
        assert payload["max_completion_tokens"] >= 1024


def test_claude_5_5_requests_omit_temperature_and_budget_for_thinking(
    monkeypatch: MonkeyPatch,
) -> None:
    """Claude 5.5 models 400 on any non-default temperature; thinking counts toward max_tokens."""

    captured = _capture_requests(
        monkeypatch,
        {"content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "Good fit."}]},
    )

    result = _enrich(Settings(LLM_PROVIDER="claude", CLAUDE_API_KEY="test-key"))

    assert result is not None and result.summary == "Good fit."
    payload = captured[0]
    assert payload["model"] == "claude-haiku-5-5"
    assert {"temperature", "top_p", "top_k"}.isdisjoint(payload)
    assert payload["output_config"] == {"effort": "low"}
    assert payload["max_tokens"] >= 1024


def test_gemini_3_requests_use_thinking_level_instead_of_sampling(
    monkeypatch: MonkeyPatch,
) -> None:
    """Gemini 3.6+ ignores custom sampling; thinking tokens count toward the output cap."""

    captured = _capture_requests(
        monkeypatch, {"candidates": [{"content": {"parts": [{"text": "Fit."}]}}]}
    )

    _enrich(Settings(LLM_PROVIDER="gemini", GEMINI_API_KEY="test-key"))
    _enrich(
        Settings(LLM_PROVIDER="gemini", GEMINI_API_KEY="test-key", GEMINI_MODEL="gemini-2.5-flash")
    )

    current, legacy = (payload["generationConfig"] for payload in captured)
    assert isinstance(current, dict) and isinstance(legacy, dict)
    assert "temperature" not in current
    assert current["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert current["maxOutputTokens"] >= 1024
    assert "thinkingConfig" not in legacy


@pytest.mark.parametrize("model", ["gemini-4-hydrogen", "gemini-4-carbon", "gemini-4-argon"])
def test_gemini_4_requests_think_low_without_a_small_output_cap(
    monkeypatch: MonkeyPatch, model: str
) -> None:
    """Gemini 4 caps thinking plus reply together: a small cap can end the turn empty."""

    captured = _capture_requests(
        monkeypatch, {"candidates": [{"content": {"parts": [{"text": "Fit."}]}}]}
    )

    result = _enrich(Settings(LLM_PROVIDER="gemini", GEMINI_API_KEY="test-key", GEMINI_MODEL=model))

    assert result is not None and result.model == model
    config = captured[0]["generationConfig"]
    assert isinstance(config, dict)
    assert config["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert "maxOutputTokens" not in config
    assert {"temperature", "topP", "topK"}.isdisjoint(config)
