"""HITL post-apply follow-up cadence planner (never auto-nudges).

Closes the gap vs Teal/Huntr CRM follow-up reminders that live only inside
proprietary UIs. This service builds an offline day-offset cadence from
applied_on + preferred channels — it never emails recruiters, never
auto-closes applications, and never performs network I/O.

Distinct from ``ApplicationGhostingDetector`` (stall urgency after silence)
and ``RecruiterOutreachDraftService`` (cold outreach drafts). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_OFFSETS_DAYS: tuple[int, ...] = (3, 7, 14)


@dataclass(slots=True, frozen=True)
class FollowUpStep:
    """One human-approved follow-up step in a cadence."""

    day_offset: int
    channel: str
    action: str


@dataclass(slots=True, frozen=True)
class FollowUpCadencePlan:
    """Human-reviewable post-apply follow-up cadence (never auto-nudges)."""

    company: str
    role: str
    applied_on: str
    steps: list[FollowUpStep]
    guidance: list[str]
    requires_human_review: bool
    auto_nudge: bool


class ApplicationFollowUpCadencePlanner:
    """Build an offline post-apply HITL follow-up cadence."""

    def plan(
        self,
        *,
        company: str,
        role: str,
        applied_on: str,
        channels: list[str] | None = None,
        offsets_days: list[int] | None = None,
    ) -> FollowUpCadencePlan:
        """Assemble a day-offset follow-up cadence for human review.

        Args:
            company: Target company (required).
            role: Role title (required).
            applied_on: ISO date string when the application was sent (required).
            channels: Preferred channels in order (email/linkedin/portal).
            offsets_days: Positive day offsets for follow-ups (default 3/7/14).

        Returns:
            FollowUpCadencePlan with ``requires_human_review=True`` and
            ``auto_nudge=False``.

        Raises:
            ValueError: If required fields are blank or offsets invalid.
        """

        cleaned_company = (company or "").strip()
        cleaned_role = (role or "").strip()
        cleaned_applied = (applied_on or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")
        if not cleaned_role:
            raise ValueError("role must be a non-empty string")
        if not cleaned_applied:
            raise ValueError("applied_on must be a non-empty string")

        channel_list = _clean_channels(channels)
        offsets = _clean_offsets(offsets_days)
        steps = [
            FollowUpStep(
                day_offset=offset,
                channel=channel_list[index % len(channel_list)],
                action=_action_for(offset, cleaned_role, cleaned_company),
            )
            for index, offset in enumerate(offsets)
        ]
        guidance = [
            f"{cleaned_role} @ {cleaned_company}: cadence from applied_on={cleaned_applied}.",
            "requires_human_review=True; auto_nudge=False — never auto-sends.",
            f"Planned {len(steps)} HITL follow-up step(s) across {len(channel_list)} channel(s).",
            "Skip or rewrite any step before sending; keep tone concise and specific.",
        ]
        return FollowUpCadencePlan(
            company=cleaned_company,
            role=cleaned_role,
            applied_on=cleaned_applied,
            steps=steps,
            guidance=guidance,
            requires_human_review=True,
            auto_nudge=False,
        )


def _clean_channels(channels: list[str] | None) -> list[str]:
    if not channels:
        return ["email", "linkedin"]
    cleaned = [item.strip().lower() for item in channels if item and item.strip()]
    if not cleaned:
        raise ValueError("channels must include at least one non-empty channel")
    return cleaned


def _clean_offsets(offsets_days: list[int] | None) -> list[int]:
    raw = list(offsets_days) if offsets_days is not None else list(_DEFAULT_OFFSETS_DAYS)
    if not raw:
        raise ValueError("offsets_days must not be empty")
    cleaned: list[int] = []
    for offset in raw:
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 1:
            raise ValueError("offsets_days values must be integers >= 1")
        cleaned.append(offset)
    return cleaned


def _action_for(offset: int, role: str, company: str) -> str:
    if offset <= 3:
        return f"Polite check-in on {role} @ {company} status (day +{offset})."
    if offset <= 7:
        return f"Short value-add bump for {role} @ {company} (day +{offset})."
    return f"Final low-pressure close-the-loop note for {role} @ {company} (day +{offset})."
