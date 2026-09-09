"""HITL recruiter outreach draft generator (email + LinkedIn DM).

Closes the gap vs Teal/Huntr outreach templates and LinkedIn Easy Apply flows
that auto-send messages. This service only builds drafts for human review —
it never sends email or LinkedIn DMs and never performs network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_CHANNELS = frozenset({"email", "linkedin"})


@dataclass(slots=True, frozen=True)
class RecruiterOutreachDraft:
    """Human-reviewable recruiter outreach draft (never auto-sent)."""

    channel: str
    subject: str
    body: str
    talking_points: list[str]
    requires_human_review: bool


class RecruiterOutreachDraftService:
    """Generate offline email / LinkedIn DM drafts for HITL review."""

    def generate(
        self,
        *,
        company: str,
        role: str,
        recruiter_name: str | None = None,
        channel: str = "email",
        notes: str | None = None,
    ) -> RecruiterOutreachDraft:
        """Build a structured outreach draft without sending or networking.

        Args:
            company: Target company name (required).
            role: Target role title (required for a coherent draft).
            recruiter_name: Optional recruiter / hiring-manager name.
            channel: ``email`` or ``linkedin`` (default ``email``).
            notes: Optional candidate notes to weave into talking points.

        Returns:
            RecruiterOutreachDraft with ``requires_human_review=True``.

        Raises:
            ValueError: If company is blank or channel is unsupported.
        """

        cleaned_company = (company or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")

        cleaned_channel = (channel or "").strip().lower()
        if cleaned_channel not in _ALLOWED_CHANNELS:
            raise ValueError("channel must be 'email' or 'linkedin'")

        cleaned_role = (role or "").strip() or "the open role"
        greeter = (recruiter_name or "").strip() or "there"
        note = (notes or "").strip()

        talking_points = [
            f"Express interest in the {cleaned_role} role at {cleaned_company}.",
            "Reference one concrete outcome from your recent work that maps to the JD.",
            "Ask one clarifying question about team priorities or success metrics.",
        ]
        if note:
            talking_points.append(f"Incorporate candidate note: {note}")

        if cleaned_channel == "email":
            subject = f"Interest in {cleaned_role} at {cleaned_company}"
            body = (
                f"Hi {greeter},\n\n"
                f"I am writing to express interest in the {cleaned_role} role at "
                f"{cleaned_company}. I have reviewed the posting and would welcome "
                f"a short conversation about how my background maps to the team's needs.\n\n"
                f"Happy to share a tailored resume or portfolio on request.\n\n"
                f"Best regards,\n"
                f"[Your Name]\n"
                f"\n"
                f"— Draft only: human review required; do not auto-send —"
            )
        else:
            subject = f"LinkedIn DM · {cleaned_role} @ {cleaned_company}"
            body = (
                f"Hi {greeter} — I saw the {cleaned_role} opening at {cleaned_company} "
                f"and would love to connect. Happy to share a concise note on fit "
                f"if helpful. Thanks!\n"
                f"\n"
                f"— Draft only: human review required; do not auto-send —"
            )

        return RecruiterOutreachDraft(
            channel=cleaned_channel,
            subject=subject,
            body=body,
            talking_points=talking_points,
            requires_human_review=True,
        )
