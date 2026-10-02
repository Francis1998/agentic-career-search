"""HITL EmployeeVolunteerHoursGapAdvisor (offline; never auto-acts).

Closes the gap vs Benevity/VolunteerMatch/Levels.fyi/Blind volunteer-hours planners
locked in closed UIs. Emits coverage bands —
never auto-acts and never performs network I/O.

Distinct from ``BackupCareDaysGapAdvisor`` and
``WellnessStipendGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EmployeeVolunteerHoursGapReport:
    """Human-reviewable coverage report."""

    needed_hours_per_year: float
    employer_volunteer_hours: float
    planned_hours: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_log: bool


class EmployeeVolunteerHoursGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        needed_hours_per_year: float,
        employer_volunteer_hours: float,
        planned_hours: float,
    ) -> EmployeeVolunteerHoursGapReport:
        """Compute coverage band.

        Args:
            needed_hours_per_year: Need amount (``> 0``).
            employer_volunteer_hours: Employer provided amount (``> 0``).
            planned_hours: Planned usage/cover (``>= 0``).

        Returns:
            EmployeeVolunteerHoursGapReport with ``auto_log=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if needed_hours_per_year <= 0:
            raise ValueError("needed_hours_per_year must be > 0")
        if employer_volunteer_hours <= 0:
            raise ValueError("employer_volunteer_hours must be > 0")
        if planned_hours < 0:
            raise ValueError("planned_hours must be >= 0")

        covered = min(employer_volunteer_hours, planned_hours)
        coverage_ratio = round(covered / needed_hours_per_year, 4)
        remaining_cap = round(max(employer_volunteer_hours - planned_hours, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Coverage math is advisory; verify plan documents and tax treatment.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Benefit covers most need; confirm enrollment windows.")
        elif band == "partial_gap":
            guidance.append("Partial gap; budget out-of-pocket or supplemental cover.")
        else:
            guidance.append("Benefit thin vs need; negotiate or buy supplemental cover.")

        return EmployeeVolunteerHoursGapReport(
            needed_hours_per_year=float(needed_hours_per_year),
            employer_volunteer_hours=float(employer_volunteer_hours),
            planned_hours=float(planned_hours),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_log=False,
        )
