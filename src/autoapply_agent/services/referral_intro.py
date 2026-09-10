"""HITL referral intro draft service (warm-intro email drafts).

Closes the gap vs LinkedIn InMail auto-templates and Teal/Huntr referral trackers
that either auto-send or leave intros unstructured. This service only builds
offline warm-intro drafts for human review — it never sends email, never DMs
contacts, and never performs network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_CHANNELS = frozenset({"email", "linkedin"})


@dataclass(slots=True, frozen=True)
class ReferralIntroDraft:
    """Human-reviewable warm-intro draft (never auto-sent)."""

    channel: str
    subject: str
    body: str
    talking_points: list[str]
    requires_human_review: bool


class ReferralIntroDraftService:
    """Generate offline warm-intro email / LinkedIn drafts for HITL review."""

    def generate(
        self,
        *,
        company: str,
        role: str,
        connector_name: str,
        mutual_context: str,
        channel: str = "email",
    ) -> ReferralIntroDraft:
        """Build a structured referral intro draft without sending or networking.

        Args:
            company: Target company (required).
            role: Target role title (required for coherent draft).
            connector_name: Person who can introduce you (required).
            mutual_context: Shared context / why they are a fit connector (required).
            channel: ``email`` or ``linkedin`` (default ``email``).

        Returns:
            ReferralIntroDraft with ``requires_human_review=True``.

        Raises:
            ValueError: If required fields blank or channel unsupported.
        """

        cleaned_company = (company or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")

        cleaned_connector = (connector_name or "").strip()
        if not cleaned_connector:
            raise ValueError("connector_name must be a non-empty string")

        cleaned_context = (mutual_context or "").strip()
        if not cleaned_context:
            raise ValueError("mutual_context must be a non-empty string")

        cleaned_channel = (channel or "").strip().lower()
        if cleaned_channel not in _ALLOWED_CHANNELS:
            raise ValueError("channel must be 'email' or 'linkedin'")

        cleaned_role = (role or "").strip() or "the open role"

        talking_points = [
            f"Ask {cleaned_connector} for a warm intro to the {cleaned_role} team "
            f"at {cleaned_company}.",
            f"Reference mutual context: {cleaned_context}.",
            "Offer a short blurb the connector can forward unchanged.",
            "Make it easy to decline — never pressure the connector.",
        ]

        if cleaned_channel == "email":
            subject = f"Quick ask: intro to {cleaned_role} at {cleaned_company}?"
            body = (
                f"Hi {cleaned_connector},\n\n"
                f"I hope you are well. I am exploring the {cleaned_role} role at "
                f"{cleaned_company} and thought of you because {cleaned_context}.\n\n"
                f"If you are comfortable, would you be open to a brief warm intro to "
                f"the hiring team? Happy to send a 3-sentence blurb you can forward "
                f"as-is. Totally fine if now is not a good time.\n\n"
                f"Thank you,\n"
                f"[Your Name]\n"
                f"\n"
                f"— Draft only: human review required; do not auto-send —"
            )
        else:
            subject = f"LinkedIn DM · intro ask · {cleaned_role} @ {cleaned_company}"
            body = (
                f"Hi {cleaned_connector} — exploring {cleaned_role} at {cleaned_company} "
                f"and thought of you given {cleaned_context}. Open to a short warm intro "
                f"if comfortable? Easy to decline. Thanks!\n"
                f"\n"
                f"— Draft only: human review required; do not auto-send —"
            )

        return ReferralIntroDraft(
            channel=cleaned_channel,
            subject=subject,
            body=body,
            talking_points=talking_points,
            requires_human_review=True,
        )
