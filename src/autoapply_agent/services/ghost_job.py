"""HITL ghost-job signal flagger (offline cues; never auto-applies).

Closes the gap vs Teal / Simplify / Huntr evergreen / ghost-job detectors
locked behind proprietary boards. Flags local JD text for reuse cues,
missing salary, impossible seniority stacks, and forever-open language —
never auto-applies and never performs network I/O.

Distinct from ``JobPostingFreshnessScorer`` (age_days bands) and
``ApplicationGhostingDetector`` (post-apply stall). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_SIGNAL_CUES: tuple[tuple[str, tuple[str, ...], str, int], ...] = (
    (
        "evergreen_language",
        (
            "always hiring",
            "evergreen",
            "rolling basis",
            "ongoing hiring",
            "applications accepted year-round",
        ),
        "Evergreen / always-open language may indicate a non-urgent listing.",
        2,
    ),
    (
        "missing_comp",
        ("competitive salary", "doe", "salary commensurate", "comp DOE"),
        "Vague compensation language without a numeric band.",
        1,
    ),
    (
        "impossible_stack",
        (
            "5+ years rust and 5+ years cobol",
            "10+ years kubernetes",
            "expert in every cloud",
            "unicorn",
        ),
        "Unrealistic stacked seniority / technology demands.",
        3,
    ),
    (
        "repost_cues",
        ("reposted", "re-listed", "backfill evergreen", "same req #"),
        "Repost / re-list cues often correlate with ghost or slow pipelines.",
        2,
    ),
    (
        "no_hiring_manager",
        ("talent community", "join our talent network", "general interest"),
        "Talent-network phrasing without a concrete req owner.",
        1,
    ),
)


@dataclass(slots=True, frozen=True)
class GhostJobSignal:
    """One ghost-job risk signal."""

    kind: str
    weight: int
    evidence: list[str]
    rationale: str


@dataclass(slots=True, frozen=True)
class GhostJobReport:
    """Human-reviewable ghost-job risk report."""

    signals: list[GhostJobSignal]
    risk_score: float
    risk_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_apply: bool


class GhostJobSignalFlagger:
    """Flag ghost / evergreen JD risk cues offline (HITL only)."""

    def flag(self, job_description: str, *, has_salary_band: bool = False) -> GhostJobReport:
        """Flag ghost-job signals from JD text.

        Args:
            job_description: Target JD text (required).
            has_salary_band: When False and vague-comp cues hit, adds missing_comp.

        Returns:
            GhostJobReport with ``auto_apply=False``.

        Raises:
            ValueError: If JD blank.
        """

        jd = (job_description or "").strip()
        if not jd:
            raise ValueError("job_description must be a non-empty string")

        lowered = jd.lower()
        signals: list[GhostJobSignal] = []
        for kind, cues, rationale, weight in _SIGNAL_CUES:
            if kind == "missing_comp" and has_salary_band:
                continue
            hits = [cue for cue in cues if cue in lowered]
            if hits:
                signals.append(
                    GhostJobSignal(
                        kind=kind,
                        weight=weight,
                        evidence=hits,
                        rationale=rationale,
                    )
                )

        raw = sum(signal.weight for signal in signals)
        # Cap score at 1.0 for HITL banding.
        risk_score = round(min(1.0, raw / 6.0), 3)
        if risk_score >= 0.67:
            band = "high"
        elif risk_score >= 0.34:
            band = "medium"
        elif risk_score > 0:
            band = "low"
        else:
            band = "clear"

        guidance = [
            "Ghost-job signals are advisory; a human decides whether to apply.",
            "Do not auto-apply from this flagger.",
        ]
        if band in {"medium", "high"}:
            guidance.append(
                "Consider verifying req owner, salary band, and last-active hiring manager."
            )
        if band == "clear":
            guidance.append("No strong ghost cues — still confirm freshness separately.")

        return GhostJobReport(
            signals=signals,
            risk_score=risk_score,
            risk_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_apply=False,
        )
