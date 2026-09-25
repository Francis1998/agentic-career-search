"""HITL on-call stipend vs load gap advisor (offline; never auto-accepts).

Closes the gap vs Levels.fyi / Blind / Candor on-call compensation calculators
locked in closed UIs. Given weekly on-call hours, hourly on-call rate or flat
monthly stipend, and expected page burden, emits value bands — never
auto-accepts and never performs network I/O.

Distinct from ``CommuteCostTradeoffAdvisor`` and ``PtoCashOutValueAdvisor``.
Optional later polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2
must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_WEEKS_PER_YEAR = 48.0


@dataclass(slots=True, frozen=True)
class OnCallStipendGapReport:
    """Human-reviewable on-call stipend vs load report."""

    weekly_oncall_hours: float
    hourly_oncall_rate: float
    monthly_flat_stipend: float
    expected_pages_per_week: float
    annual_value_usd: float
    load_index: float
    value_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class OnCallStipendGapAdvisor:
    """Advise on-call stipend adequacy vs load."""

    def advise(
        self,
        *,
        weekly_oncall_hours: float,
        hourly_oncall_rate: float = 0.0,
        monthly_flat_stipend: float = 0.0,
        expected_pages_per_week: float = 0.0,
    ) -> OnCallStipendGapReport:
        """Compute on-call value band vs load.

        Args:
            weekly_oncall_hours: Scheduled on-call hours/week (``>= 0``).
            hourly_oncall_rate: Extra USD/hour while on-call (``>= 0``).
            monthly_flat_stipend: Flat monthly on-call stipend USD (``>= 0``).
            expected_pages_per_week: Expected pages/week (``>= 0``).

        Returns:
            OnCallStipendGapReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if weekly_oncall_hours < 0:
            raise ValueError("weekly_oncall_hours must be >= 0")
        if hourly_oncall_rate < 0:
            raise ValueError("hourly_oncall_rate must be >= 0")
        if monthly_flat_stipend < 0:
            raise ValueError("monthly_flat_stipend must be >= 0")
        if expected_pages_per_week < 0:
            raise ValueError("expected_pages_per_week must be >= 0")

        annual_from_hours = weekly_oncall_hours * hourly_oncall_rate * _WEEKS_PER_YEAR
        annual_from_flat = monthly_flat_stipend * 12.0
        annual_value = round(annual_from_hours + annual_from_flat, 2)
        # Load index mixes hours and pages (pages weighted x2 hours-equivalent).
        load_index = round(weekly_oncall_hours + expected_pages_per_week * 2.0, 4)
        dollars_per_load = annual_value / max(load_index * _WEEKS_PER_YEAR, 1.0)

        if load_index == 0:
            band = "no_load"
        elif dollars_per_load >= 25.0:
            band = "adequate"
        elif dollars_per_load >= 10.0:
            band = "thin"
        else:
            band = "underpaid"

        guidance = [
            "On-call stipend math is advisory; verify rotation and escalation policy.",
            "Do not auto-accept on-call terms from this advisor.",
        ]
        if band == "no_load":
            guidance.append("No on-call load modeled; confirm rotation expectations.")
        elif band == "adequate":
            guidance.append("Compensation looks adequate vs modeled load.")
        elif band == "thin":
            guidance.append("Thin pay vs load; negotiate higher stipend or fewer weeks.")
        else:
            guidance.append("Underpaid vs load; escalate before accepting the rotation.")

        return OnCallStipendGapReport(
            weekly_oncall_hours=float(weekly_oncall_hours),
            hourly_oncall_rate=float(hourly_oncall_rate),
            monthly_flat_stipend=float(monthly_flat_stipend),
            expected_pages_per_week=float(expected_pages_per_week),
            annual_value_usd=float(annual_value),
            load_index=float(load_index),
            value_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )
