"""HITL 401(k) employer-match gap advisor (offline; never auto-enrolls).

Closes the gap vs Levels.fyi / Fidelity / Candor match calculators locked in
closed UIs. Given employer match percent, market match percent, and salary,
emits annual match-dollar gap bands — never auto-enrolls and never performs
network I/O.

Distinct from ``EsppDiscountValueAdvisor`` (ESPP discount) and
``SalaryBandEstimator`` (cash band). Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class FourOhOneKMatchGapReport:
    """Human-reviewable 401(k) match gap report."""

    employer_match_pct: float
    market_match_pct: float
    salary: float
    annual_gap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class FourOhOneKMatchGapAdvisor:
    """Advise 401(k) employer-match gap vs market."""

    def advise(
        self,
        *,
        employer_match_pct: float,
        market_match_pct: float,
        salary: float,
    ) -> FourOhOneKMatchGapReport:
        """Compute annual match-dollar gap and coverage band.

        Args:
            employer_match_pct: Employer match percent (``>= 0``).
            market_match_pct: Market/reference match percent (``>= 0``).
            salary: Annual salary USD (``> 0``).

        Returns:
            FourOhOneKMatchGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if employer_match_pct < 0:
            raise ValueError("employer_match_pct must be >= 0")
        if market_match_pct < 0:
            raise ValueError("market_match_pct must be >= 0")
        if salary <= 0:
            raise ValueError("salary must be > 0")

        annual_gap = round(
            (market_match_pct - employer_match_pct) / 100.0 * salary,
            2,
        )
        if annual_gap <= 0:
            band = "strong"
        elif annual_gap < salary * 0.02:
            band = "parity"
        else:
            band = "gap"

        guidance = [
            "401(k) match math is advisory; verify plan documents.",
            "Do not auto-enroll or change deferrals from this advisor.",
        ]
        if band == "gap":
            guidance.append("Employer match trails market by >=2% of salary; ask about true-up.")
        elif band == "parity":
            guidance.append("Near-market match; confirm vesting schedule and true-up timing.")
        else:
            guidance.append("Employer match meets or beats market; prioritize maxing the match.")

        return FourOhOneKMatchGapReport(
            employer_match_pct=float(employer_match_pct),
            market_match_pct=float(market_match_pct),
            salary=float(salary),
            annual_gap_usd=float(annual_gap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
