"""HITL LinkedIn headline keyword scorer (offline cues; never auto-posts).

Closes the gap vs Careerflow / Taplio / LinkedIn Premium headline graders
locked in proprietary UIs. This service scores an offline LinkedIn headline
against target role keywords for HITL edits — it never auto-posts profile
updates and never performs network I/O.

Distinct from ``AtsKeywordCoverageScorer`` (resume vs JD keywords) and
``SkillsProfileFitScorer`` (skills inventory fit). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*")


@dataclass(slots=True, frozen=True)
class LinkedInHeadlineReport:
    """Human-reviewable LinkedIn headline keyword coverage report."""

    present_keywords: list[str]
    missing_keywords: list[str]
    coverage_score: float
    guidance: list[str]
    requires_human_review: bool
    auto_post: bool


class LinkedInHeadlineKeywordScorer:
    """Score LinkedIn headline token overlap vs target role keywords (HITL)."""

    def score(self, headline: str, target_keywords: list[str]) -> LinkedInHeadlineReport:
        """Score headline coverage against target keywords.

        Args:
            headline: LinkedIn headline text (required).
            target_keywords: Non-empty list of role keywords to cover.

        Returns:
            LinkedInHeadlineReport with ``requires_human_review=True`` and
            ``auto_post=False``.

        Raises:
            ValueError: If headline is blank or keywords empty/blank.
        """

        cleaned = (headline or "").strip()
        if not cleaned:
            raise ValueError("headline must be a non-empty string")
        if not target_keywords:
            raise ValueError("target_keywords must be a non-empty list")

        normalized: list[str] = []
        seen: set[str] = set()
        for raw in target_keywords:
            kw = (raw or "").strip().lower()
            if not kw:
                raise ValueError("target_keywords entries must be non-empty")
            if kw not in seen:
                normalized.append(kw)
                seen.add(kw)

        tokens = set(_TOKEN_RE.findall(cleaned.lower()))
        # Also allow multi-word keyword substring matches in headline.
        lowered = cleaned.lower()
        present: list[str] = []
        missing: list[str] = []
        for kw in normalized:
            if " " in kw:
                hit = kw in lowered
            else:
                hit = kw in tokens or kw in lowered
            if hit:
                present.append(kw)
            else:
                missing.append(kw)

        score = len(present) / len(normalized)
        guidance: list[str] = []
        if missing:
            guidance.append(
                "Add HITL headline phrasing for missing keywords: "
                + ", ".join(missing[:8])
                + ("…" if len(missing) > 8 else "")
                + "."
            )
        if score >= 0.75:
            guidance.append("Strong keyword coverage; keep headline concise for HITL review.")
        elif score >= 0.4:
            guidance.append("Partial coverage; prioritize top missing role keywords in HITL edit.")
        else:
            guidance.append("Low coverage; rebuild headline around the top 3 role keywords.")

        return LinkedInHeadlineReport(
            present_keywords=present,
            missing_keywords=missing,
            coverage_score=round(score, 3),
            guidance=guidance,
            requires_human_review=True,
            auto_post=False,
        )
