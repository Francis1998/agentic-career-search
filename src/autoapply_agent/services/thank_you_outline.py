"""HITL thank-you note outline planner (post-interview; never auto-sends).

Closes the gap vs Teal/Huntr / Careerflow templates that either stay inside
closed UIs or encourage one-click sends. This service builds an offline
thank-you email/LinkedIn outline from interview notes — it never emails
recruiters, never posts to LinkedIn, and never performs network I/O.

Distinct from ``InterviewFeedbackSynthesizer`` (debrief strengths/gaps) and
``RecruiterOutreachDraftService`` (cold outreach). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ThankYouOutline:
    """Human-reviewable thank-you note outline (never auto-sends)."""

    company: str
    role: str
    interviewer: str
    channel: str
    subject: str
    beats: list[str]
    closing: str
    requires_human_review: bool
    auto_send: bool


class ThankYouNoteOutlinePlanner:
    """Plan post-interview thank-you note outlines for HITL send."""

    def plan(
        self,
        *,
        company: str,
        role: str,
        interviewer: str,
        highlights: list[str] | None = None,
        channel: str = "email",
    ) -> ThankYouOutline:
        """Build a thank-you outline from company/role/interviewer + highlights.

        Args:
            company: Interviewing company (required).
            role: Role title (required for coherent framing).
            interviewer: Interviewer name or panel label (required).
            highlights: Optional discussion highlights to weave into beats.
            channel: ``email`` or ``linkedin`` (default email).

        Returns:
            ThankYouOutline with ``requires_human_review=True`` and
            ``auto_send=False``.

        Raises:
            ValueError: If company/role/interviewer blank or channel unknown.
        """

        cleaned_company = (company or "").strip()
        cleaned_role = (role or "").strip()
        cleaned_interviewer = (interviewer or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")
        if not cleaned_role:
            raise ValueError("role must be a non-empty string")
        if not cleaned_interviewer:
            raise ValueError("interviewer must be a non-empty string")

        cleaned_channel = (channel or "email").strip().lower()
        if cleaned_channel not in {"email", "linkedin"}:
            raise ValueError("channel must be 'email' or 'linkedin'")

        cleaned_highlights = [
            item.strip() for item in (highlights or []) if isinstance(item, str) and item.strip()
        ]

        if cleaned_channel == "email":
            subject = f"Thank you — {cleaned_role} conversation"
        else:
            subject = f"Appreciate the {cleaned_role} conversation"

        beats = [
            f"Thank {cleaned_interviewer} for the {cleaned_role} discussion at {cleaned_company}.",
            "Reference one concrete topic from the interview (HITL edit before send).",
        ]
        if cleaned_highlights:
            for highlight in cleaned_highlights[:3]:
                beats.append(f"Callback beat: {highlight}.")
        else:
            beats.append("Add one callback to a project, metric, or team detail you discussed.")
        beats.append("Restate interest in the role and openness to next steps — human send only.")

        closing = "requires_human_review=True; auto_send=False — never email or DM automatically."

        return ThankYouOutline(
            company=cleaned_company,
            role=cleaned_role,
            interviewer=cleaned_interviewer,
            channel=cleaned_channel,
            subject=subject,
            beats=beats,
            closing=closing,
            requires_human_review=True,
            auto_send=False,
        )
