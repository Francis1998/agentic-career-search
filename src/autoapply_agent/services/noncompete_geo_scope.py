"""HITL NonCompeteGeoScopeAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `NoncompeteFlagger` and `OfferDeadlineAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NonCompeteGeoScopeReport:
    """Human-reviewable report."""

    restricted_radius_miles: float
    acceptable_radius_miles: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class NonCompeteGeoScopeAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        restricted_radius_miles: float,
        acceptable_radius_miles: float,
    ) -> NonCompeteGeoScopeReport:
        """Compute coverage band.

        Args:
            restricted_radius_miles: Observed metric (``> 0``).
            acceptable_radius_miles: Target value (``> 0``).

        Returns:
            NonCompeteGeoScopeReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if restricted_radius_miles <= 0:
            raise ValueError("restricted_radius_miles must be > 0")
        if acceptable_radius_miles <= 0:
            raise ValueError("acceptable_radius_miles must be > 0")

        coverage_ratio = round(
            min(restricted_radius_miles, acceptable_radius_miles) / acceptable_radius_miles,
            4,
        )
        remaining_cap = round(max(restricted_radius_miles - acceptable_radius_miles, 0.0), 2)

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

        return NonCompeteGeoScopeReport(
            restricted_radius_miles=float(restricted_radius_miles),
            acceptable_radius_miles=float(acceptable_radius_miles),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
