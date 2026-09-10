"""HITL interview feedback synthesizer (post-interview notes → debrief).

Closes the gap vs Teal/Huntr interview trackers and Notion debrief templates
that stay unstructured. This service only synthesizes offline notes for human
review — it never contacts recruiters, never writes to calendars, and never
performs network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_OUTCOMES = frozenset({"positive", "mixed", "negative", "unknown"})


@dataclass(slots=True, frozen=True)
class InterviewFeedbackBrief:
    """Human-reviewable post-interview debrief brief (never auto-sent)."""

    company: str
    role: str
    outcome_signal: str
    strengths: list[str]
    gaps: list[str]
    follow_ups: list[str]
    requires_human_review: bool


class InterviewFeedbackSynthesizer:
    """Synthesize offline post-interview notes into a structured HITL debrief."""

    def synthesize(
        self,
        *,
        company: str,
        role: str,
        notes: str,
        outcome_signal: str = "unknown",
    ) -> InterviewFeedbackBrief:
        """Build a structured debrief from free-text interview notes.

        Args:
            company: Interviewing company (required).
            role: Role title (required for coherent framing).
            notes: Candidate or interviewer notes (required).
            outcome_signal: ``positive``, ``mixed``, ``negative``, or ``unknown``.

        Returns:
            InterviewFeedbackBrief with ``requires_human_review=True``.

        Raises:
            ValueError: If company/notes are blank or outcome_signal is invalid.
        """

        cleaned_company = (company or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")

        cleaned_notes = (notes or "").strip()
        if not cleaned_notes:
            raise ValueError("notes must be a non-empty string")

        cleaned_outcome = (outcome_signal or "").strip().lower() or "unknown"
        if cleaned_outcome not in _ALLOWED_OUTCOMES:
            raise ValueError("outcome_signal must be one of: positive, mixed, negative, unknown")

        cleaned_role = (role or "").strip() or "the open role"
        tokens = [token for token in cleaned_notes.replace(",", " ").split() if token]

        strengths = [
            f"Captured concrete interview signal for {cleaned_role} at {cleaned_company}.",
            "Preserve exact quotes and interviewer names before polishing with GPT-5.5 / "
            "Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.",
        ]
        if len(tokens) >= 8:
            strengths.append("Notes include enough detail for a STAR-style write-up.")

        gaps = [
            "Confirm what was promised vs what still needs a follow-up email.",
            "Flag any question you deferred and prepare a written answer.",
        ]
        if cleaned_outcome in {"mixed", "negative"}:
            gaps.append("Identify one recovery action before the next loop.")

        follow_ups = [
            f"Send a thank-you note for the {cleaned_role} loop at {cleaned_company} "
            "(human review required; do not auto-send).",
            "Update ApplicationStageTracker notes with this debrief.",
        ]
        if cleaned_outcome == "positive":
            follow_ups.append("Prepare negotiation inputs if an offer is likely.")

        return InterviewFeedbackBrief(
            company=cleaned_company,
            role=cleaned_role,
            outcome_signal=cleaned_outcome,
            strengths=strengths,
            gaps=gaps,
            follow_ups=follow_ups,
            requires_human_review=True,
        )
