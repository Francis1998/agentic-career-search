"""HITL job posting freshness scorer (age bands; never auto-applies).

Closes the gap vs Teal/Huntr/Simplify boards that hide posting age inside
proprietary UIs. This service scores a posting by ``age_days`` into
fresh/aging/stale/expired bands with human-review guidance — it never
auto-applies and never performs network I/O.

Distinct from ``CrossSourceJobDeduper`` (near-duplicate clustering). Optional
later polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay
advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class JobFreshnessAdvice:
    """Human-reviewable job posting freshness advisory (never auto-applies)."""

    age_days: int
    band: str
    freshness_score: float
    title: str
    company: str
    guidance: list[str]
    requires_human_review: bool
    auto_apply: bool


class JobPostingFreshnessScorer:
    """Score job posting age into HITL freshness bands."""

    def score(
        self,
        *,
        age_days: int,
        title: str = "",
        company: str = "",
    ) -> JobFreshnessAdvice:
        """Map posting age to a freshness band and advisory guidance.

        Args:
            age_days: Days since the posting was published (must be >= 0).
            title: Optional job title for guidance framing.
            company: Optional company for guidance framing.

        Returns:
            JobFreshnessAdvice with ``requires_human_review=True`` and
            ``auto_apply=False``.

        Raises:
            ValueError: If age_days is negative.
        """

        if age_days < 0:
            raise ValueError("age_days must be >= 0")

        cleaned_title = (title or "").strip()
        cleaned_company = (company or "").strip()
        band = _band_for(age_days)
        freshness_score = _score_for(age_days, band)
        guidance = _guidance_for(
            age_days=age_days,
            band=band,
            freshness_score=freshness_score,
            title=cleaned_title,
            company=cleaned_company,
        )

        return JobFreshnessAdvice(
            age_days=age_days,
            band=band,
            freshness_score=freshness_score,
            title=cleaned_title,
            company=cleaned_company,
            guidance=guidance,
            requires_human_review=True,
            auto_apply=False,
        )


def _band_for(age_days: int) -> str:
    if age_days <= 7:
        return "fresh"
    if age_days <= 21:
        return "aging"
    if age_days <= 45:
        return "stale"
    return "expired"


def _score_for(age_days: int, band: str) -> float:
    if band == "fresh":
        # 0 days → 1.0, 7 days → 0.75
        return round(1.0 - (age_days / 7.0) * 0.25, 3)
    if band == "aging":
        # 8 days → ~0.74, 21 days → 0.40
        return round(0.75 - ((age_days - 8) / 13.0) * 0.35, 3)
    if band == "stale":
        # 22 days → ~0.39, 45 days → 0.15
        return round(0.40 - ((age_days - 22) / 23.0) * 0.25, 3)
    # expired: 46+ → under 0.15, floor at 0.0
    return round(max(0.0, 0.14 - ((age_days - 46) / 60.0) * 0.14), 3)


def _guidance_for(
    *,
    age_days: int,
    band: str,
    freshness_score: float,
    title: str,
    company: str,
) -> list[str]:
    label = title or "role"
    if company:
        label = f"{label} @ {company}"
    lines = [
        f"{label}: age_days={age_days}, band={band}, freshness_score={freshness_score:.3f}.",
        "requires_human_review=True; auto_apply=False — never auto-applies.",
    ]
    if band == "fresh":
        lines.append("Prioritize tailored draft while the posting is still warm.")
    elif band == "aging":
        lines.append("Apply soon if fit is high; confirm the role is still open (HITL).")
    elif band == "stale":
        lines.append("Verify listing status before investing a deep application.")
    else:
        lines.append("Likely filled or evergreen — deprioritize unless recruiter-confirmed.")
    return lines
