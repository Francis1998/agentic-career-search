"""HITL PaidFamilyLeaveStateGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `BereavementLeaveGapAdvisor` and `BackupCareDaysGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PaidFamilyLeaveStateGapReport:
    """Human-reviewable report."""

    employer_weeks: float
    state_mandated_weeks: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class PaidFamilyLeaveStateGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        employer_weeks: float,
        state_mandated_weeks: float,
    ) -> PaidFamilyLeaveStateGapReport:
        """Compute coverage band.

        Args:
            employer_weeks: Observed employer PFL weeks (``> 0``).
            state_mandated_weeks: State-mandated weeks (``> 0``).

        Returns:
            PaidFamilyLeaveStateGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if employer_weeks <= 0:
            raise ValueError("employer_weeks must be > 0")
        if state_mandated_weeks <= 0:
            raise ValueError("state_mandated_weeks must be > 0")

        coverage_ratio = round(
            min(employer_weeks, state_mandated_weeks) / state_mandated_weeks,
            4,
        )
        remaining_cap = round(max(employer_weeks - state_mandated_weeks, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Advisory math only; verify against primary sources.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Coverage looks adequate for HITL confirmation.")
        elif band == "partial_gap":
            guidance.append("Partial gap; renegotiate or top-up before accepting.")
        else:
            guidance.append("Under-covered; escalate for human decision.")

        return PaidFamilyLeaveStateGapReport(
            employer_weeks=float(employer_weeks),
            state_mandated_weeks=float(state_mandated_weeks),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
