"""HITL IsoEarlyExerciseAmtLadderAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `IsoAmtExposureAdvisor` (bargain-element snapshot) / `EsppLookbackGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IsoEarlyExerciseAmtLadderReport:
    """Human-reviewable report."""

    ladder_years: float
    needed_years: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class IsoEarlyExerciseAmtLadderAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        ladder_years: float,
        needed_years: float,
    ) -> IsoEarlyExerciseAmtLadderReport:
        """Compute coverage band.

        Args:
            ladder_years: Observed value (>= 0).
            needed_years: Target value (> 0).

        Returns:
            IsoEarlyExerciseAmtLadderReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if ladder_years < 0:
            raise ValueError("ladder_years must be >= 0")
        if needed_years <= 0:
            raise ValueError("needed_years must be > 0")

        coverage_ratio = round(min(ladder_years, needed_years) / needed_years, 4)
        remaining_cap = round(max(needed_years - ladder_years, 0.0), 2)

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

        return IsoEarlyExerciseAmtLadderReport(
            ladder_years=float(ladder_years),
            needed_years=float(needed_years),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
