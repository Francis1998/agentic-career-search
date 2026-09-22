"""HITL severance package gap advisor (offline; never auto-accepts).

Closes the gap vs Levels.fyi / Blind / Candor severance calculators locked in
closed UIs. Given tenure years and offered severance weeks, emits coverage
bands vs a simple tenure-scaled expectation — never auto-accepts offers and
never performs network I/O.

Distinct from ``SigningBonusClawbackAdvisor`` (clawback liability) and
``OfferCompareMatrix`` (multi-offer ranking). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SeverancePackageGapReport:
    """Human-reviewable severance coverage report."""

    tenure_years: float
    offered_weeks: float
    expected_weeks: float
    coverage_ratio: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class SeverancePackageGapAdvisor:
    """Advise severance coverage vs a tenure-scaled week expectation."""

    def __init__(self, *, weeks_per_year: float = 2.0, floor_weeks: float = 4.0) -> None:
        """Create an advisor.

        Args:
            weeks_per_year: Expected severance weeks accrued per tenure year.
            floor_weeks: Minimum expected weeks regardless of tenure.

        Raises:
            ValueError: On non-positive parameters.
        """

        if weeks_per_year <= 0:
            raise ValueError("weeks_per_year must be > 0")
        if floor_weeks <= 0:
            raise ValueError("floor_weeks must be > 0")
        self._weeks_per_year = float(weeks_per_year)
        self._floor_weeks = float(floor_weeks)

    def advise(
        self,
        *,
        tenure_years: float,
        offered_weeks: float,
    ) -> SeverancePackageGapReport:
        """Compute severance coverage vs tenure-scaled expectation.

        Args:
            tenure_years: Years of tenure (``>= 0``).
            offered_weeks: Severance weeks offered (``>= 0``).

        Returns:
            SeverancePackageGapReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if tenure_years < 0:
            raise ValueError("tenure_years must be >= 0")
        if offered_weeks < 0:
            raise ValueError("offered_weeks must be >= 0")

        expected = max(self._floor_weeks, tenure_years * self._weeks_per_year)
        ratio = offered_weeks / expected if expected > 0 else 0.0

        if ratio >= 1.0:
            band = "meets_or_exceeds"
        elif ratio >= 0.75:
            band = "near_gap"
        elif ratio >= 0.4:
            band = "material_gap"
        else:
            band = "severe_gap"

        guidance = [
            "Severance math is advisory; verify with the separation agreement.",
            "Do not auto-accept from this advisor.",
        ]
        if band == "meets_or_exceeds":
            guidance.append("Offered weeks meet or exceed the tenure-scaled heuristic.")
        elif band == "near_gap":
            guidance.append("Offered weeks are close; negotiate top-up or benefits runway.")
        else:
            guidance.append(
                f"Coverage ratio {ratio:.0%} vs expected {expected:.1f} weeks; "
                "ask for more weeks or COBRA/runway support."
            )

        return SeverancePackageGapReport(
            tenure_years=float(tenure_years),
            offered_weeks=float(offered_weeks),
            expected_weeks=float(expected),
            coverage_ratio=float(ratio),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )
