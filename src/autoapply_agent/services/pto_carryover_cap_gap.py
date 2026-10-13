"""HITL PtoCarryoverCapGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `PtoAccrualCliffAdvisor` / `PtoCashOutValueAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PtoCarryoverCapGapReport:
    """Human-reviewable report."""

    carryover_hours: float
    needed_hours: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class PtoCarryoverCapGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        carryover_hours: float,
        needed_hours: float,
    ) -> PtoCarryoverCapGapReport:
        """Compute coverage band.

        Args:
            carryover_hours: Observed value (>= 0).
            needed_hours: Target value (> 0).

        Returns:
            PtoCarryoverCapGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if carryover_hours < 0:
            raise ValueError("carryover_hours must be >= 0")
        if needed_hours <= 0:
            raise ValueError("needed_hours must be > 0")

        coverage_ratio = round(min(carryover_hours, needed_hours) / needed_hours, 4)
        remaining_cap = round(max(needed_hours - carryover_hours, 0.0), 2)

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
            guidance.append("Partial gap; renegotiate terms carefully.")
        else:
            guidance.append("Under-covered; escalate for human decision.")

        return PtoCarryoverCapGapReport(
            carryover_hours=float(carryover_hours),
            needed_hours=float(needed_hours),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
