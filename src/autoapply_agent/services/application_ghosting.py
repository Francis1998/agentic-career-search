"""HITL application ghosting detector (stalled-pipeline advisory; never auto-nudges).

Closes the gap vs Teal/Huntr CRM views that surface "no reply" only inside
proprietary UIs. This service computes offline stall urgency from stage +
last-update timestamps and emits human-review follow-up suggestions — it
never emails recruiters, never auto-closes applications, and never performs
network I/O.

Distinct from ``ApplicationStageTracker`` (stage transitions only) and
``OfferDeadlineTracker`` (offer countdown). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class GhostingStatus:
    """Human-reviewable stalled-application advisory (never auto-nudges)."""

    company: str
    role: str
    stage: str
    last_update_iso: str
    now_iso: str
    days_stalled: int
    urgency: str
    suggestions: list[str]
    requires_human_review: bool
    auto_nudge: bool


class ApplicationGhostingDetector:
    """Detect stalled applications with offline urgency + HITL suggestions."""

    def detect(
        self,
        *,
        company: str,
        role: str,
        stage: str,
        last_update_iso: str,
        now_iso: str,
    ) -> GhostingStatus:
        """Compute stall days, urgency, and human-review follow-up suggestions.

        Args:
            company: Target company (required).
            role: Role title (required for coherent framing).
            stage: Pipeline stage label (e.g. applied, interview).
            last_update_iso: Last activity as ISO date or datetime.
            now_iso: Reference "now" as ISO date or datetime.

        Returns:
            GhostingStatus with ``requires_human_review=True`` and
            ``auto_nudge=False``.

        Raises:
            ValueError: If company blank or dates cannot be parsed.
        """

        cleaned_company = (company or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")

        last_update = _parse_iso(last_update_iso, field="last_update_iso")
        now = _parse_iso(now_iso, field="now_iso")

        cleaned_role = (role or "").strip() or "the open role"
        cleaned_stage = (stage or "").strip().lower() or "applied"
        days_stalled = (now.date() - last_update.date()).days
        if days_stalled < 0:
            raise ValueError("last_update_iso must not be after now_iso")

        urgency = _urgency_for(days_stalled, cleaned_stage)
        suggestions = _suggestions_for(
            company=cleaned_company,
            role=cleaned_role,
            stage=cleaned_stage,
            days_stalled=days_stalled,
            urgency=urgency,
        )

        return GhostingStatus(
            company=cleaned_company,
            role=cleaned_role,
            stage=cleaned_stage,
            last_update_iso=last_update_iso.strip(),
            now_iso=now_iso.strip(),
            days_stalled=days_stalled,
            urgency=urgency,
            suggestions=suggestions,
            requires_human_review=True,
            auto_nudge=False,
        )


def _parse_iso(value: str, *, field: str) -> datetime:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field} must be a non-empty ISO date or datetime")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO date or datetime") from exc


def _urgency_for(days_stalled: int, stage: str) -> str:
    """Map stall days (+ stage bias) to urgency labels."""

    interview_bias = 3 if stage in {"interview", "onsite", "final"} else 0
    effective = days_stalled + interview_bias
    if effective >= 21:
        return "likely_ghosted"
    if effective >= 14:
        return "stalled"
    if effective >= 7:
        return "cooling"
    return "fresh"


def _suggestions_for(
    *,
    company: str,
    role: str,
    stage: str,
    days_stalled: int,
    urgency: str,
) -> list[str]:
    """Build HITL follow-up suggestions (never auto-sent)."""

    suggestions = [
        f"Review {company} / {role} ({stage}) after {days_stalled} day(s) with no update.",
        "Draft a polite follow-up for human send — never auto-nudge.",
        "requires_human_review=True; auto_nudge=False.",
    ]
    if urgency == "likely_ghosted":
        suggestions.append("Consider closing as ghosted in your CRM after a final HITL ping.")
    elif urgency == "stalled":
        suggestions.append("Prefer a short status-check email over a new full application.")
    elif urgency == "cooling":
        suggestions.append("Optional LinkedIn view of the hiring manager — still HITL only.")
    else:
        suggestions.append("No chase needed yet; keep monitoring locally.")
    return suggestions
