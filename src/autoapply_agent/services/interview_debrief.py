"""HITL interview debrief checklist (post-interview reflection; never auto-sends).

Closes the gap vs Teal/Huntr post-interview trackers that bury reflection prompts
inside closed UIs. This service builds an offline structured checklist from
what-went-well / gaps / follow-ups — it never contacts recruiters, never
auto-sends notes, and never performs network I/O.

Distinct from ``ThankYouNoteOutlinePlanner`` (outbound thank-you outlines),
``InterviewPrepBriefService`` (pre-interview prep), and
``InterviewFeedbackSynthesizer`` (free-text note synthesis). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class InterviewDebriefPlan:
    """Human-reviewable post-interview debrief checklist (never auto-sent)."""

    company: str
    role: str
    what_went_well: list[str]
    gaps: list[str]
    follow_ups: list[str]
    checklist: list[str]
    guidance: list[str]
    requires_human_review: bool
    auto_submit: bool


class InterviewDebriefChecklist:
    """Build an offline post-interview HITL debrief checklist."""

    def build(
        self,
        *,
        company: str,
        role: str,
        what_went_well: list[str] | None = None,
        gaps: list[str] | None = None,
        follow_ups: list[str] | None = None,
    ) -> InterviewDebriefPlan:
        """Assemble a structured debrief checklist for human review.

        Args:
            company: Interviewing company (required).
            role: Role title (required).
            what_went_well: Strength bullets from the candidate (optional).
            gaps: Gap bullets to revisit (optional).
            follow_ups: Explicit follow-up actions (optional).

        Returns:
            InterviewDebriefPlan with ``requires_human_review=True`` and
            ``auto_submit=False``.

        Raises:
            ValueError: If company or role is blank.
        """

        cleaned_company = (company or "").strip()
        cleaned_role = (role or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")
        if not cleaned_role:
            raise ValueError("role must be a non-empty string")

        strengths = _clean_items(what_went_well)
        gap_items = _clean_items(gaps)
        follow_items = _clean_items(follow_ups)
        checklist = _checklist_for(
            company=cleaned_company,
            role=cleaned_role,
            strengths=strengths,
            gaps=gap_items,
            follow_ups=follow_items,
        )
        guidance = _guidance_for(
            company=cleaned_company,
            role=cleaned_role,
            strengths=strengths,
            gaps=gap_items,
            follow_ups=follow_items,
        )

        return InterviewDebriefPlan(
            company=cleaned_company,
            role=cleaned_role,
            what_went_well=strengths,
            gaps=gap_items,
            follow_ups=follow_items,
            checklist=checklist,
            guidance=guidance,
            requires_human_review=True,
            auto_submit=False,
        )


def _clean_items(items: list[str] | None) -> list[str]:
    if not items:
        return []
    return [item.strip() for item in items if item and item.strip()]


def _checklist_for(
    *,
    company: str,
    role: str,
    strengths: list[str],
    gaps: list[str],
    follow_ups: list[str],
) -> list[str]:
    lines = [
        f"Review debrief for {role} @ {company} before any recruiter contact.",
        "Confirm what went well and capture reusable STAR stories.",
        "Mark each gap with a concrete practice action.",
        "Approve follow-ups manually — never auto-send notes.",
    ]
    for item in strengths:
        lines.append(f"Strength to reuse: {item}")
    for item in gaps:
        lines.append(f"Gap to close: {item}")
    for item in follow_ups:
        lines.append(f"Follow-up (HITL only): {item}")
    return lines


def _guidance_for(
    *,
    company: str,
    role: str,
    strengths: list[str],
    gaps: list[str],
    follow_ups: list[str],
) -> list[str]:
    lines = [
        f"{role} @ {company}: offline debrief checklist ready for human review.",
        "requires_human_review=True; auto_submit=False — never auto-sends notes.",
        f"Captured {len(strengths)} strengths, {len(gaps)} gaps, {len(follow_ups)} follow-ups.",
    ]
    if not strengths and not gaps and not follow_ups:
        lines.append("Add at least one strength, gap, or follow-up before filing.")
    elif gaps and not follow_ups:
        lines.append("Consider one HITL follow-up tied to the largest gap.")
    else:
        lines.append("Keep thank-you notes separate via ThankYouNoteOutlinePlanner.")
    return lines
