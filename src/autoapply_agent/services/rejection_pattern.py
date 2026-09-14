"""HITL rejection-pattern analyzer (offline themes; never auto-rewrites).

Closes the gap vs Teal Insights / Huntr analytics that bury rejection themes
inside proprietary dashboards. This service clusters offline free-text
rejection reasons into coarse themes and HITL next actions — it never
rewrites resumes, never auto-applies, and never performs network I/O.

Distinct from ``SkillGapLearningPathPlanner`` (skill milestones) and
``AtsKeywordCoverageScorer`` (resume↔JD keyword coverage). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_THEME_CUES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "experience_depth",
        ("experience", "senior", "years", "junior", "level"),
        "Strengthen quantified impact stories for the target seniority.",
    ),
    (
        "skills_mismatch",
        ("skill", "stack", "python", "java", "kubernetes", "sql", "missing"),
        "Map missing skills to a focused practice plan before re-applying.",
    ),
    (
        "process_fit",
        ("culture", "team", "fit", "collaboration", "communication"),
        "Prepare concrete collaboration examples tailored to the team.",
    ),
    (
        "timing_headcount",
        ("headcount", "freeze", "budget", "timing", "filled", "another candidate"),
        "Keep rapport warm and revisit when hiring reopens.",
    ),
)


@dataclass(slots=True, frozen=True)
class RejectionTheme:
    """One clustered rejection theme with supporting evidence."""

    theme: str
    count: int
    examples: list[str]
    suggested_action: str


@dataclass(slots=True, frozen=True)
class RejectionPatternReport:
    """Human-reviewable rejection-pattern report (never auto-rewrites)."""

    themes: list[RejectionTheme]
    uncategorized: list[str]
    guidance: list[str]
    requires_human_review: bool
    auto_rewrite: bool


class RejectionPatternAnalyzer:
    """Cluster offline rejection reasons into HITL themes."""

    def analyze(self, reasons: list[str] | None) -> RejectionPatternReport:
        """Cluster rejection reasons into themes for human review.

        Args:
            reasons: Free-text rejection notes (required non-empty list).

        Returns:
            RejectionPatternReport with ``requires_human_review=True`` and
            ``auto_rewrite=False``.

        Raises:
            ValueError: If ``reasons`` is empty after cleaning.
        """

        cleaned = _clean_reasons(reasons)
        if not cleaned:
            raise ValueError("reasons must include at least one non-empty string")

        buckets: dict[str, list[str]] = {name: [] for name, _cues, _action in _THEME_CUES}
        uncategorized: list[str] = []
        for reason in cleaned:
            lowered = reason.lower()
            matched = False
            for name, cues, _action in _THEME_CUES:
                if any(cue in lowered for cue in cues):
                    buckets[name].append(reason)
                    matched = True
                    break
            if not matched:
                uncategorized.append(reason)

        themes: list[RejectionTheme] = []
        for name, _cues, action in _THEME_CUES:
            examples = buckets[name]
            if not examples:
                continue
            themes.append(
                RejectionTheme(
                    theme=name,
                    count=len(examples),
                    examples=examples[:3],
                    suggested_action=action,
                )
            )
        themes.sort(key=lambda item: (-item.count, item.theme))
        guidance = [
            f"Clustered {len(cleaned)} rejection note(s) into {len(themes)} theme(s).",
            "requires_human_review=True; auto_rewrite=False — never auto-edits resumes.",
            "Treat themes as hypotheses; verify against full interview notes.",
        ]
        if uncategorized:
            guidance.append(f"{len(uncategorized)} note(s) were uncategorized — review manually.")
        return RejectionPatternReport(
            themes=themes,
            uncategorized=uncategorized,
            guidance=guidance,
            requires_human_review=True,
            auto_rewrite=False,
        )


def _clean_reasons(reasons: list[str] | None) -> list[str]:
    if not reasons:
        return []
    return [item.strip() for item in reasons if item and item.strip()]
