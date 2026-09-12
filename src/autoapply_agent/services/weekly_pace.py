"""HITL weekly application pace advisor (burnout guard; never auto-submits).

Closes the gap vs Teal Insights / Huntr analytics dashboards that visualize
apply volume inside closed UIs without a local, offline pace advisor. This
service compares planned vs target weekly applications and emits human-review
throttle/boost guidance — it never submits applications and never performs
network I/O.

Distinct from ``ApplicationStageTracker`` (CRM transitions) and
``ApplicationGhostingDetector`` (stall detection). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class WeeklyPaceAdvice:
    """Human-reviewable weekly application pace advisory (never auto-submits)."""

    week_label: str
    planned_applications: int
    target_applications: int
    pace_ratio: float
    band: str
    guidance: list[str]
    requires_human_review: bool
    auto_submit: bool


class WeeklyApplicationPaceAdvisor:
    """Advise weekly application volume vs a HITL target (burnout guard)."""

    def advise(
        self,
        *,
        week_label: str,
        planned_applications: int,
        target_applications: int = 10,
    ) -> WeeklyPaceAdvice:
        """Compare planned weekly apps to a target and emit pace guidance.

        Args:
            week_label: Human label for the week (e.g. ``2026-W37``).
            planned_applications: Count of applications planned this week.
            target_applications: HITL weekly target (default 10; must be >= 1).

        Returns:
            WeeklyPaceAdvice with ``requires_human_review=True`` and
            ``auto_submit=False``.

        Raises:
            ValueError: If week_label blank, counts negative, or target < 1.
        """

        cleaned_label = (week_label or "").strip()
        if not cleaned_label:
            raise ValueError("week_label must be a non-empty string")
        if planned_applications < 0:
            raise ValueError("planned_applications must be >= 0")
        if target_applications < 1:
            raise ValueError("target_applications must be >= 1")

        pace_ratio = planned_applications / float(target_applications)
        band = _band_for(pace_ratio)
        guidance = _guidance_for(
            week_label=cleaned_label,
            planned=planned_applications,
            target=target_applications,
            band=band,
            pace_ratio=pace_ratio,
        )

        return WeeklyPaceAdvice(
            week_label=cleaned_label,
            planned_applications=planned_applications,
            target_applications=target_applications,
            pace_ratio=round(pace_ratio, 3),
            band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_submit=False,
        )


def _band_for(pace_ratio: float) -> str:
    if pace_ratio < 0.5:
        return "under_pace"
    if pace_ratio <= 1.25:
        return "on_pace"
    if pace_ratio <= 1.75:
        return "hot"
    return "overload"


def _guidance_for(
    *,
    week_label: str,
    planned: int,
    target: int,
    band: str,
    pace_ratio: float,
) -> list[str]:
    lines = [
        f"{week_label}: {planned}/{target} planned applications (ratio={pace_ratio:.2f}).",
        "requires_human_review=True; auto_submit=False — never auto-apply.",
    ]
    if band == "under_pace":
        lines.append("Consider sourcing 2-3 extra high-fit roles (HITL only).")
    elif band == "on_pace":
        lines.append("Hold quality bar; prefer tailored drafts over spray volume.")
    elif band == "hot":
        lines.append("Throttle low-fit boards; keep interview prep capacity free.")
    else:
        lines.append("Burnout risk: cut spray applies and block calendar for recovery/prep.")
    return lines
