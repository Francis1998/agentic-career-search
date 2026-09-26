"""HITL sabbatical eligibility advisor (offline; never auto-approves).

Closes the gap vs Levels.fyi / Blind / Candor sabbatical / tenure-leave
planners locked in closed UIs. Given tenure years, policy years, offered
sabbatical weeks, and market weeks, emits eligibility bands — never
auto-approves and never performs network I/O.

Distinct from ``ParentalLeaveGapAdvisor`` (parental leave) and
``PtoCashOutValueAdvisor`` (PTO cash-out). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SabbaticalEligibilityReport:
    """Human-reviewable sabbatical eligibility report."""

    tenure_years: float
    policy_years: float
    sabbatical_weeks_offered: int
    market_weeks: int
    tenure_ratio: float
    weeks_ratio: float
    eligibility_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_approve: bool


class SabbaticalEligibilityAdvisor:
    """Advise sabbatical eligibility from tenure and offered weeks."""

    def advise(
        self,
        *,
        tenure_years: float,
        policy_years: float,
        sabbatical_weeks_offered: int,
        market_weeks: int,
    ) -> SabbaticalEligibilityReport:
        """Compute sabbatical eligibility band.

        Args:
            tenure_years: Years of continuous tenure (``>= 0``).
            policy_years: Policy years required before sabbatical (``> 0``).
            sabbatical_weeks_offered: Offered sabbatical weeks (``>= 0``).
            market_weeks: Market-typical sabbatical weeks (``> 0``).

        Returns:
            SabbaticalEligibilityReport with ``auto_approve=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if tenure_years < 0:
            raise ValueError("tenure_years must be >= 0")
        if policy_years <= 0:
            raise ValueError("policy_years must be > 0")
        if sabbatical_weeks_offered < 0:
            raise ValueError("sabbatical_weeks_offered must be >= 0")
        if market_weeks <= 0:
            raise ValueError("market_weeks must be > 0")

        tenure_ratio = round(tenure_years / policy_years, 4)
        weeks_ratio = round(sabbatical_weeks_offered / float(market_weeks), 4)

        if tenure_ratio >= 1.0 and weeks_ratio >= 0.8:
            band = "eligible"
        elif tenure_ratio >= 0.8:
            band = "near_eligible"
        else:
            band = "ineligible_thin"

        guidance = [
            "Sabbatical eligibility is advisory; verify written policy and manager approval.",
            "Do not auto-approve sabbatical leave from this advisor.",
        ]
        if band == "eligible":
            guidance.append("Tenure and offered weeks look policy-ready; confirm blackout dates.")
        elif band == "near_eligible":
            guidance.append("Close to policy tenure; plan the request window with HR.")
        else:
            guidance.append("Tenure/weeks thin vs policy/market; escalate before relying on leave.")

        return SabbaticalEligibilityReport(
            tenure_years=float(tenure_years),
            policy_years=float(policy_years),
            sabbatical_weeks_offered=int(sabbatical_weeks_offered),
            market_weeks=int(market_weeks),
            tenure_ratio=float(tenure_ratio),
            weeks_ratio=float(weeks_ratio),
            eligibility_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_approve=False,
        )
