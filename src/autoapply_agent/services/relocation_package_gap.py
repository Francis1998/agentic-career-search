"""HITL relocation package gap advisor (offline; never auto-accepts).

Closes the gap vs Huntr / Teal / Levels.fyi offer tools that bury relocation
math in closed UIs. Compares offered relocation stipend vs estimated move cost
and emits coverage bands — never auto-accepts and never performs network I/O.

Distinct from ``LocationRemoteFitScorer`` (geo/remote preference fit) and
``OfferCompareMatrix`` (cash+equity totals). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RelocationPackageGapReport:
    """Human-reviewable relocation stipend vs estimated cost report."""

    offered_stipend: float
    estimated_move_cost: float
    gap_amount: float
    coverage_ratio: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class RelocationPackageGapAdvisor:
    """Advise whether a relocation stipend covers estimated move costs."""

    def advise(
        self,
        *,
        offered_stipend: float,
        estimated_move_cost: float,
    ) -> RelocationPackageGapReport:
        """Compare offered stipend against estimated move cost.

        Args:
            offered_stipend: Employer relocation stipend USD (``>= 0``).
            estimated_move_cost: Candidate-estimated move cost USD (``>= 0``).

        Returns:
            RelocationPackageGapReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_stipend < 0:
            raise ValueError("offered_stipend must be >= 0")
        if estimated_move_cost < 0:
            raise ValueError("estimated_move_cost must be >= 0")

        gap = round(estimated_move_cost - offered_stipend, 2)
        if estimated_move_cost == 0:
            ratio = 1.0 if offered_stipend == 0 else float("inf")
        else:
            ratio = offered_stipend / estimated_move_cost

        if estimated_move_cost == 0 and offered_stipend == 0:
            band = "unknown"
        elif ratio >= 1.0:
            band = "fully_covered"
        elif ratio >= 0.75:
            band = "mostly_covered"
        elif ratio >= 0.4:
            band = "partial_gap"
        else:
            band = "large_gap"

        guidance = [
            "Relocation coverage is advisory; verify receipts and tax treatment.",
            "Do not auto-accept from this advisor.",
        ]
        if band == "large_gap":
            guidance.append(f"Stipend leaves ~${gap:,.0f} uncovered; negotiate or budget cash.")
        elif band == "fully_covered":
            guidance.append("Stipend appears to cover the estimated move cost.")
        elif band == "unknown":
            guidance.append("Provide stipend and cost estimates to score coverage.")
        else:
            guidance.append(f"Coverage ratio ~{ratio:.0%}; consider negotiating the residual gap.")

        return RelocationPackageGapReport(
            offered_stipend=float(offered_stipend),
            estimated_move_cost=float(estimated_move_cost),
            gap_amount=float(gap),
            coverage_ratio=float(ratio) if ratio != float("inf") else 1.0,
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )
