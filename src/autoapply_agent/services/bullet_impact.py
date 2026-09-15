"""HITL resume bullet impact scorer (offline metrics cues; never auto-rewrites).

Closes the gap vs Teal Insights / Jobscan / Resume Worded dashboards that score
bullet strength only inside proprietary UIs. This service scans offline resume
bullets for quantified impact (%, $, x multipliers, user/scale counts) and
returns HITL guidance — it never rewrites bullets and never performs network I/O.

Distinct from ``AtsKeywordCoverageScorer`` (keyword coverage) and
``RejectionPatternAnalyzer`` (rejection themes). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PERCENT_RE = re.compile(r"(?<!\w)\d{1,3}(?:\.\d+)?%")
_MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?[kKmMbB]?\b")
_MULTIPLIER_RE = re.compile(r"\b\d+(?:\.\d+)?\s?x\b", re.IGNORECASE)
_SCALE_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s*[kKmMbB]?\+?\s*"
    r"(?:users?|customers?|requests?|qps|rps|devices?|"
    r"merchants?|transactions?|seats?|employees?|engineers?)\b",
    re.IGNORECASE,
)
_ACTION_CUES: tuple[str, ...] = (
    "led",
    "owned",
    "shipped",
    "launched",
    "reduced",
    "increased",
    "improved",
    "cut",
    "grew",
    "built",
    "designed",
    "automated",
)


@dataclass(slots=True, frozen=True)
class BulletImpactScore:
    """Impact score for one resume bullet."""

    bullet: str
    score: float
    band: str
    cues: list[str]


@dataclass(slots=True, frozen=True)
class BulletImpactReport:
    """Human-reviewable bullet impact report (never auto-rewrites)."""

    bullets_scored: list[BulletImpactScore]
    average_score: float
    weak_bullets: list[str]
    guidance: list[str]
    requires_human_review: bool
    auto_rewrite: bool


class ResumeBulletImpactScorer:
    """Score offline resume bullets for quantified impact (HITL only)."""

    def score(self, bullets: list[str] | None) -> BulletImpactReport:
        """Score resume bullets for quantified impact cues.

        Args:
            bullets: Resume bullet strings (required non-empty after cleaning).

        Returns:
            BulletImpactReport with ``requires_human_review=True`` and
            ``auto_rewrite=False``.

        Raises:
            ValueError: If no non-empty bullets remain.
        """

        cleaned = [item.strip() for item in (bullets or []) if item and item.strip()]
        if not cleaned:
            raise ValueError("bullets must include at least one non-empty string")

        scored: list[BulletImpactScore] = []
        for bullet in cleaned:
            cues: list[str] = []
            points = 0.0
            if _PERCENT_RE.search(bullet):
                cues.append("percent")
                points += 0.35
            if _MONEY_RE.search(bullet):
                cues.append("money")
                points += 0.35
            if _MULTIPLIER_RE.search(bullet):
                cues.append("multiplier")
                points += 0.2
            if _SCALE_RE.search(bullet):
                cues.append("scale")
                points += 0.25
            lowered = bullet.lower()
            if any(re.search(rf"\b{re.escape(cue)}\b", lowered) for cue in _ACTION_CUES):
                cues.append("action_verb")
                points += 0.15
            score = min(1.0, round(points, 2))
            if score >= 0.75:
                band = "strong"
            elif score >= 0.4:
                band = "moderate"
            else:
                band = "weak"
            scored.append(BulletImpactScore(bullet=bullet, score=score, band=band, cues=cues))

        average = round(sum(item.score for item in scored) / len(scored), 2)
        weak = [item.bullet for item in scored if item.band == "weak"]
        guidance = [
            f"Scored {len(scored)} bullet(s); average_score={average}.",
            "requires_human_review=True; auto_rewrite=False — never auto-edits resumes.",
            "Prefer adding %/$/scale metrics over adjective inflation.",
        ]
        if weak:
            guidance.append(f"{len(weak)} weak bullet(s) lack quantified impact — revise manually.")
        return BulletImpactReport(
            bullets_scored=scored,
            average_score=average,
            weak_bullets=weak,
            guidance=guidance,
            requires_human_review=True,
            auto_rewrite=False,
        )
