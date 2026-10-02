"""HITL MentalHealthEapSessionGapAdvisor (offline; never auto-acts).

Closes the gap vs Lyra/Spring Health/Modern Health/Levels.fyi EAP session planners
locked in closed UIs. Emits coverage bands —
never auto-acts and never performs network I/O.

Distinct from ``WellnessStipendGapAdvisor`` and
``LegalInsuranceGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MentalHealthEapSessionGapReport:
    """Human-reviewable coverage report."""

    needed_sessions_per_year: float
    employer_session_cap: float
    planned_sessions: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_book: bool


class MentalHealthEapSessionGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        needed_sessions_per_year: float,
        employer_session_cap: float,
        planned_sessions: float,
    ) -> MentalHealthEapSessionGapReport:
        """Compute coverage band.

        Args:
            needed_sessions_per_year: Need amount (``> 0``).
            employer_session_cap: Employer provided amount (``> 0``).
            planned_sessions: Planned usage/cover (``>= 0``).

        Returns:
            MentalHealthEapSessionGapReport with ``auto_book=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if needed_sessions_per_year <= 0:
            raise ValueError("needed_sessions_per_year must be > 0")
        if employer_session_cap <= 0:
            raise ValueError("employer_session_cap must be > 0")
        if planned_sessions < 0:
            raise ValueError("planned_sessions must be >= 0")

        covered = min(employer_session_cap, planned_sessions)
        coverage_ratio = round(covered / needed_sessions_per_year, 4)
        remaining_cap = round(max(employer_session_cap - planned_sessions, 0.0), 2)

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

        return MentalHealthEapSessionGapReport(
            needed_sessions_per_year=float(needed_sessions_per_year),
            employer_session_cap=float(employer_session_cap),
            planned_sessions=float(planned_sessions),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_book=False,
        )
