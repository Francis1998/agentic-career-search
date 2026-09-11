"""HITL offer deadline tracker (countdown + reminders; never auto-decline).

Closes the gap vs Teal/Huntr offer trackers that lack local deadline
countdowns and urgency reminders. This service only computes offline
urgency and human-review reminders — it never declines offers, never
emails recruiters, and never performs network I/O.

Optional later polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2
must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class OfferDeadlineStatus:
    """Human-reviewable offer deadline countdown (never auto-declines)."""

    company: str
    role: str
    deadline_iso: str
    now_iso: str
    days_remaining: int
    urgency: str
    reminders: list[str]
    requires_human_review: bool
    auto_decline: bool


class OfferDeadlineTracker:
    """Track offer deadlines with offline urgency + HITL reminders."""

    def track(
        self,
        *,
        company: str,
        role: str,
        deadline_iso: str,
        now_iso: str,
    ) -> OfferDeadlineStatus:
        """Compute days remaining, urgency, and human-review reminders.

        Args:
            company: Offering company (required).
            role: Role title (required for coherent framing).
            deadline_iso: Offer deadline as ISO date or datetime.
            now_iso: Reference "now" as ISO date or datetime.

        Returns:
            OfferDeadlineStatus with ``requires_human_review=True`` and
            ``auto_decline=False``.

        Raises:
            ValueError: If company blank or dates cannot be parsed.
        """

        cleaned_company = (company or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")

        deadline = _parse_iso(deadline_iso, field="deadline_iso")
        now = _parse_iso(now_iso, field="now_iso")

        cleaned_role = (role or "").strip() or "the open role"
        days_remaining = (deadline.date() - now.date()).days
        urgency = _urgency_for(days_remaining)
        reminders = _reminders_for(
            company=cleaned_company,
            role=cleaned_role,
            days_remaining=days_remaining,
            urgency=urgency,
        )

        return OfferDeadlineStatus(
            company=cleaned_company,
            role=cleaned_role,
            deadline_iso=deadline_iso.strip(),
            now_iso=now_iso.strip(),
            days_remaining=days_remaining,
            urgency=urgency,
            reminders=reminders,
            requires_human_review=True,
            auto_decline=False,
        )


def _parse_iso(value: str, *, field: str) -> datetime:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field} must be a valid ISO date or datetime")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO date or datetime") from exc


def _urgency_for(days_remaining: int) -> str:
    if days_remaining < 0:
        return "overdue"
    if days_remaining == 0:
        return "due_today"
    if days_remaining <= 3:
        return "due_soon"
    return "upcoming"


def _reminders_for(
    *,
    company: str,
    role: str,
    days_remaining: int,
    urgency: str,
) -> list[str]:
    reminders = [
        f"Review the {role} offer from {company} before responding "
        "(human review required; never auto-decline).",
        "Confirm deadline timezone and written terms with a human before any reply.",
        "Optional polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 "
        "must stay advisory.",
    ]
    if urgency == "overdue":
        reminders.insert(
            0,
            f"Deadline passed by {abs(days_remaining)} day(s) — ask a human whether "
            "an extension is still possible (do not auto-decline).",
        )
    elif urgency == "due_today":
        reminders.insert(
            0,
            "Offer deadline is today — prepare accept/counter/decline options for "
            "human decision (never auto-decline).",
        )
    elif urgency == "due_soon":
        reminders.insert(
            0,
            f"{days_remaining} day(s) remaining — schedule HITL review of accept vs "
            "counter vs decline paths.",
        )
    else:
        reminders.insert(
            0,
            f"{days_remaining} day(s) remaining — keep this offer on the human "
            "review calendar; no automated response.",
        )
    return reminders
