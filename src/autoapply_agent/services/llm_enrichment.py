"""LLM enrichment service for optional agent rationale augmentation."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.core.config import Settings


@dataclass(frozen=True, slots=True)
class LLMEnrichmentResult:
    """Represents one normalized LLM enrichment output."""

    provider: str
    model: str
    summary: str


class LLMEnrichmentService:
    """Call configured LLM providers and normalize response content."""

    def __init__(self, settings: Settings) -> None:
        """Initialize LLM enrichment service from application settings.

        Args:
            settings: Application configuration.
        """

        self._settings = settings

    async def enrich_job_decision(
        self,
        job_candidate: JobCandidate,
        query: str | None,
        deterministic_rationale: list[str],
    ) -> LLMEnrichmentResult | None:
        """Generate optional LLM summary for a job decision.

        Args:
            job_candidate: Candidate selected by source adapters.
            query: User search objective.
            deterministic_rationale: Existing non-LLM rationale lines.

        Returns:
            Normalized enrichment result when provider call succeeds, else None.
        """

        prompt = self._build_prompt(job_candidate, query, deterministic_rationale)
        try:
            if self._settings.llm_provider == "gemini":
                return await self._call_gemini(prompt)
            if self._settings.llm_provider == "kimi":
                return await self._call_kimi(prompt)
            if self._settings.llm_provider == "claude":
                return await self._call_claude(prompt)
            if self._settings.llm_provider == "gpt":
                return await self._call_gpt(prompt)
            return None
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _build_prompt(
        job_candidate: JobCandidate,
        query: str | None,
        deterministic_rationale: list[str],
    ) -> str:
        """Build compact prompt for provider-agnostic decision enrichment."""

        query_text = query or "general engineering relevance"
        rationale_blob = "\n".join(f"- {line}" for line in deterministic_rationale)
        return (
            "You are an AI career assistant. "
            "Provide a compact 1-2 sentence assessment for this role.\n"
            f"Query: {query_text}\n"
            f"Title: {job_candidate.title}\n"
            f"Company: {job_candidate.company or 'unknown'}\n"
            f"Location: {job_candidate.location or 'unknown'}\n"
            "Current deterministic rationale:\n"
            f"{rationale_blob}\n"
            "Output only the assessment text."
        )

    async def _call_gemini(self, prompt: str) -> LLMEnrichmentResult | None:
        """Call Google Gemini REST API and normalize returned summary."""

        api_key = self._settings.gemini_api_key
        if not api_key:
            return None
        model = self._settings.gemini_model
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )
        payload: dict[str, object] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 180},
        }
        timeout = httpx.Timeout(self._settings.llm_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, params={"key": api_key}, json=payload)
            response.raise_for_status()
            body = response.json()
        candidates = body["candidates"]
        parts = candidates[0]["content"]["parts"]
        summary = self._extract_text_from_parts(parts)
        if not summary:
            return None
        return LLMEnrichmentResult(provider="gemini", model=model, summary=summary)

    async def _call_kimi(self, prompt: str) -> LLMEnrichmentResult | None:
        """Call Kimi (Moonshot) OpenAI-compatible chat completions API."""

        return await self._call_openai_compatible(
            provider="kimi",
            api_key=self._settings.kimi_api_key,
            model=self._settings.kimi_model,
            base_url=self._settings.kimi_base_url,
            prompt=prompt,
        )

    async def _call_gpt(self, prompt: str) -> LLMEnrichmentResult | None:
        """Call GPT through an OpenAI-compatible chat completions API."""

        return await self._call_openai_compatible(
            provider="gpt",
            api_key=self._settings.openai_api_key,
            model=self._settings.openai_model,
            base_url=self._settings.openai_base_url,
            prompt=prompt,
        )

    async def _call_openai_compatible(
        self,
        *,
        provider: str,
        api_key: str | None,
        model: str,
        base_url: str,
        prompt: str,
    ) -> LLMEnrichmentResult | None:
        """Call an OpenAI-compatible chat completions endpoint."""

        if not api_key:
            return None
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        payload: dict[str, object] = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": 180,
            "messages": [
                {"role": "system", "content": "You produce concise role-fit summaries."},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        timeout = httpx.Timeout(self._settings.llm_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        choice = body["choices"][0]["message"]["content"]
        summary = self._normalize_text(choice)
        if not summary:
            return None
        return LLMEnrichmentResult(provider=provider, model=model, summary=summary)

    async def _call_claude(self, prompt: str) -> LLMEnrichmentResult | None:
        """Call Anthropic Claude Messages API and normalize summary text."""

        api_key = self._settings.claude_api_key
        if not api_key:
            return None
        model = self._settings.claude_model
        endpoint = "https://api.anthropic.com/v1/messages"
        payload: dict[str, object] = {
            "model": model,
            "max_tokens": 180,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        timeout = httpx.Timeout(self._settings.llm_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        chunks = body["content"]
        summary = self._extract_anthropic_text(chunks)
        if not summary:
            return None
        return LLMEnrichmentResult(provider="claude", model=model, summary=summary)

    @staticmethod
    def _extract_text_from_parts(parts: list[dict[str, object]]) -> str | None:
        """Extract text field from Gemini part list."""

        text_segments: list[str] = []
        for part in parts:
            text_value = part.get("text")
            if isinstance(text_value, str) and text_value.strip():
                text_segments.append(text_value.strip())
        return " ".join(text_segments) or None

    @staticmethod
    def _extract_anthropic_text(chunks: list[dict[str, object]]) -> str | None:
        """Extract text content from Anthropic message content chunks."""

        segments: list[str] = []
        for chunk in chunks:
            if chunk.get("type") == "text":
                text_value = chunk.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    segments.append(text_value.strip())
        return " ".join(segments) or None

    @staticmethod
    def _normalize_text(value: object) -> str | None:
        """Normalize a provider response text into a compact string."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        if isinstance(value, list):
            segments = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            if segments:
                return " ".join(segments)
        return None
