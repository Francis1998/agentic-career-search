"""HITL skill-gap learning path planner (milestones; never enrolls courses).

Closes the gap vs Teal/Simplify skill dashboards that keep learning plans
inside closed UIs. Given ``have_skills`` vs ``required_skills``, this service
emits ordered offline learning milestones and human-review guidance — it never
enrolls in courses and never performs network I/O.

Distinct from ``SkillsProfileFitScorer`` (fit scoring only). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SkillGapLearningPath:
    """Human-reviewable skill-gap learning path (never auto-enrolls)."""

    role: str
    have_skills: list[str]
    required_skills: list[str]
    missing_skills: list[str]
    milestones: list[str]
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class SkillGapLearningPathPlanner:
    """Plan ordered HITL learning milestones for missing required skills."""

    def plan(
        self,
        *,
        have_skills: list[str] | None,
        required_skills: list[str],
        role: str = "",
    ) -> SkillGapLearningPath:
        """Compare have vs required skills and emit an ordered learning path.

        Args:
            have_skills: Skills the candidate already has (case-insensitive).
            required_skills: Skills required by the target role (non-empty).
            role: Optional role label for guidance framing.

        Returns:
            SkillGapLearningPath with ``requires_human_review=True`` and
            ``auto_enroll=False``.

        Raises:
            ValueError: If required_skills is empty or whitespace-only.
        """

        cleaned_required = _clean_skills(required_skills)
        if not cleaned_required:
            raise ValueError("required_skills must contain at least one non-empty skill")

        cleaned_have = _clean_skills(have_skills)
        have_norm = {_normalize(skill) for skill in cleaned_have}
        missing = [skill for skill in cleaned_required if _normalize(skill) not in have_norm]
        cleaned_role = (role or "").strip()
        milestones = _milestones_for(missing)
        guidance = _guidance_for(
            role=cleaned_role,
            have=cleaned_have,
            required=cleaned_required,
            missing=missing,
        )

        return SkillGapLearningPath(
            role=cleaned_role,
            have_skills=cleaned_have,
            required_skills=cleaned_required,
            missing_skills=missing,
            milestones=milestones,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )


def _clean_skills(skills: list[str] | None) -> list[str]:
    if not skills:
        return []
    return [skill.strip() for skill in skills if skill and skill.strip()]


def _normalize(skill: str) -> str:
    return skill.strip().lower()


def _milestones_for(missing: list[str]) -> list[str]:
    milestones: list[str] = []
    for index, skill in enumerate(missing, start=1):
        milestones.append(
            f"Milestone {index}: practice {skill} with a small HITL project, "
            "then self-review before claiming proficiency."
        )
    return milestones


def _guidance_for(
    *,
    role: str,
    have: list[str],
    required: list[str],
    missing: list[str],
) -> list[str]:
    label = role or "target role"
    lines = [
        f"{label}: have={len(have)}, required={len(required)}, missing={len(missing)}.",
        "requires_human_review=True; auto_enroll=False — never enrolls courses.",
    ]
    if not missing:
        lines.append("No gaps vs required skills — maintain practice cadence.")
    else:
        lines.append(f"Work milestones in order; start with '{missing[0]}' before later gaps.")
        lines.append("Use SkillsProfileFitScorer for fit scoring; this planner only paths gaps.")
    return lines
