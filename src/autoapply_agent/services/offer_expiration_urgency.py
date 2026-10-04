"""HITL OfferExpirationUrgencyAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `OfferDeadlineTracker` and `NegotiationTalkingPointsService`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class OfferExpirationUrgencyReport:
    """Human-reviewable report."""

    days_until_expire: float
    min_decision_days: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class OfferExpirationUrgencyAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        days_until_expire: float,
        min_decision_days: float,
    ) -> OfferExpirationUrgencyReport:
        """Compute coverage band.

        Args:
            days_until_expire: Observed available quantity (``> 0``).
            min_decision_days: Required quantity (``> 0``).

        Returns:
            OfferExpirationUrgencyReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if days_until_expire <= 0:
            raise ValueError("days_until_expire must be > 0")
        if min_decision_days <= 0:
            raise ValueError("min_decision_days must be > 0")

        coverage_ratio = round(
            min(days_until_expire, min_decision_days) / min_decision_days,
            4,
        )
        remaining_cap = round(max(days_until_expire - min_decision_days, 0.0), 2)

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

        return OfferExpirationUrgencyReport(
            days_until_expire=float(days_until_expire),
            min_decision_days=float(min_decision_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
