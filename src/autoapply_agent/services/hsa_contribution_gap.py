"""HITL HSA contribution vs IRS-limit gap advisor (offline; never auto-enrolls).

Closes the gap vs Fidelity / HealthEquity / Levels.fyi HSA contribution
planners locked in closed UIs. Given employee YTD, employer YTD, and the
applicable IRS annual limit, emits remaining-room coverage bands — never
auto-enrolls and never performs network I/O.

Distinct from ``FourOhOneKMatchGapAdvisor`` (401k match) and
``EsppDiscountValueAdvisor`` (ESPP). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class HsaContributionGapReport:
    """Human-reviewable HSA contribution room report."""

    employee_ytd_usd: float
    employer_ytd_usd: float
    irs_limit_usd: float
    total_ytd_usd: float
    remaining_room_usd: float
    coverage_ratio: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class HsaContributionGapAdvisor:
    """Advise HSA YTD contributions vs the applicable IRS annual limit."""

    def advise(
        self,
        *,
        employee_ytd_usd: float,
        employer_ytd_usd: float,
        irs_limit_usd: float,
    ) -> HsaContributionGapReport:
        """Compute remaining HSA contribution room band.

        Args:
            employee_ytd_usd: Employee YTD HSA deferrals (``>= 0``).
            employer_ytd_usd: Employer YTD HSA contributions (``>= 0``).
            irs_limit_usd: Applicable IRS annual limit (``> 0``).

        Returns:
            HsaContributionGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if employee_ytd_usd < 0:
            raise ValueError("employee_ytd_usd must be >= 0")
        if employer_ytd_usd < 0:
            raise ValueError("employer_ytd_usd must be >= 0")
        if irs_limit_usd <= 0:
            raise ValueError("irs_limit_usd must be > 0")

        total = round(employee_ytd_usd + employer_ytd_usd, 2)
        remaining = round(max(0.0, irs_limit_usd - total), 2)
        coverage = round(min(total / irs_limit_usd, 1.0), 4)

        if coverage >= 1.0:
            band = "fully_funded"
        elif coverage >= 0.6:
            band = "partial_gap"
        else:
            band = "under_contributing"

        guidance = [
            "HSA contribution math is advisory; verify HDHP eligibility and IRS limits.",
            "Do not auto-enroll payroll deferrals from this advisor.",
        ]
        if band == "fully_funded":
            guidance.append("YTD contributions meet or exceed the modeled IRS limit.")
        elif band == "partial_gap":
            guidance.append(
                f"About ${remaining:,.0f} IRS room remains; confirm catch-up eligibility."
            )
        else:
            guidance.append(
                "YTD HSA funding is thin vs the IRS limit; review payroll deferral before year-end."
            )

        return HsaContributionGapReport(
            employee_ytd_usd=float(employee_ytd_usd),
            employer_ytd_usd=float(employer_ytd_usd),
            irs_limit_usd=float(irs_limit_usd),
            total_ytd_usd=float(total),
            remaining_room_usd=float(remaining),
            coverage_ratio=float(coverage),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )
