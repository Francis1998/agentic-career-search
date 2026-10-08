"""HITL MealStipendGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `WellnessStipendGapAdvisor` and `HomeOfficeStipendGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MealStipendGapReport:
    """Human-reviewable report."""

    stipend_usd: float
    monthly_food_cost_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class MealStipendGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        stipend_usd: float,
        monthly_food_cost_usd: float,
    ) -> MealStipendGapReport:
        """Compute coverage band.

        Args:
            stipend_usd: Observed metric (``> 0``).
            monthly_food_cost_usd: Target value (``> 0``).

        Returns:
            MealStipendGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if stipend_usd <= 0:
            raise ValueError("stipend_usd must be > 0")
        if monthly_food_cost_usd <= 0:
            raise ValueError("monthly_food_cost_usd must be > 0")

        coverage_ratio = round(
            min(stipend_usd, monthly_food_cost_usd) / monthly_food_cost_usd,
            4,
        )
        remaining_cap = round(max(stipend_usd - monthly_food_cost_usd, 0.0), 2)

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

        return MealStipendGapReport(
            stipend_usd=float(stipend_usd),
            monthly_food_cost_usd=float(monthly_food_cost_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
