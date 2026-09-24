"""HITL commute vs remote-stipend tradeoff advisor (offline; never auto-accepts).

Closes the gap vs Blind / Levels.fyi / RemoteOK commute vs stipend math locked
in closed UIs. Given one-way commute minutes, office days/week, hourly time
value, optional transit cost, and monthly remote stipend, emits annual
tradeoff bands — never auto-accepts and never performs network I/O.

Distinct from ``RemoteTimezoneOverlapAdvisor`` (timezone overlap) and
``RelocationPackageGapAdvisor`` (relocation stipend). Optional later polish
via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_WEEKS_PER_YEAR = 48.0


@dataclass(slots=True, frozen=True)
class CommuteCostTradeoffReport:
    """Human-reviewable commute vs stipend tradeoff report."""

    commute_minutes_one_way: float
    office_days_per_week: float
    hourly_time_value: float
    weekly_transit_cost: float
    remote_stipend_monthly: float
    annual_commute_cost_usd: float
    annual_stipend_usd: float
    net_delta_usd: float
    tradeoff_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class CommuteCostTradeoffAdvisor:
    """Advise commute cost vs remote stipend tradeoff."""

    def advise(
        self,
        *,
        commute_minutes_one_way: float,
        office_days_per_week: float,
        hourly_time_value: float,
        weekly_transit_cost: float = 0.0,
        remote_stipend_monthly: float = 0.0,
    ) -> CommuteCostTradeoffReport:
        """Compute annual commute cost vs stipend and tradeoff band.

        Args:
            commute_minutes_one_way: One-way commute minutes (``>= 0``).
            office_days_per_week: Office days per week (``0..7``).
            hourly_time_value: Opportunity cost USD/hour (``> 0``).
            weekly_transit_cost: Transit/parking USD per week (``>= 0``).
            remote_stipend_monthly: Remote/WFH stipend USD/month (``>= 0``).

        Returns:
            CommuteCostTradeoffReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if commute_minutes_one_way < 0:
            raise ValueError("commute_minutes_one_way must be >= 0")
        if office_days_per_week < 0 or office_days_per_week > 7:
            raise ValueError("office_days_per_week must be between 0 and 7")
        if hourly_time_value <= 0:
            raise ValueError("hourly_time_value must be > 0")
        if weekly_transit_cost < 0:
            raise ValueError("weekly_transit_cost must be >= 0")
        if remote_stipend_monthly < 0:
            raise ValueError("remote_stipend_monthly must be >= 0")

        weekly_hours = (commute_minutes_one_way * 2.0 / 60.0) * office_days_per_week
        weekly_cost = weekly_hours * hourly_time_value + weekly_transit_cost
        annual_commute = round(weekly_cost * _WEEKS_PER_YEAR, 2)
        annual_stipend = round(remote_stipend_monthly * 12.0, 2)
        net_delta = round(annual_stipend - annual_commute, 2)

        # net_burden = commute cost not covered by stipend.
        net_burden = annual_commute - annual_stipend
        threshold = max(500.0, annual_commute * 0.1 if annual_commute else 500.0)
        if net_burden >= threshold:
            band = "favor_remote"
        elif annual_commute < threshold and net_burden <= 0:
            band = "favor_office"
        else:
            band = "mixed"

        guidance = [
            "Commute vs stipend math is advisory; verify policy and tax treatment.",
            "Do not auto-accept office or remote terms from this advisor.",
        ]
        if band == "favor_remote":
            guidance.append(
                "Commute burden exceeds stipend; negotiate WFH days or a higher stipend."
            )
        elif band == "favor_office":
            guidance.append("Commute is light and covered; office path is reasonable on dollars.")
        else:
            guidance.append("Tradeoff is mixed; weigh career/network benefits beyond dollars.")

        return CommuteCostTradeoffReport(
            commute_minutes_one_way=float(commute_minutes_one_way),
            office_days_per_week=float(office_days_per_week),
            hourly_time_value=float(hourly_time_value),
            weekly_transit_cost=float(weekly_transit_cost),
            remote_stipend_monthly=float(remote_stipend_monthly),
            annual_commute_cost_usd=float(annual_commute),
            annual_stipend_usd=float(annual_stipend),
            net_delta_usd=float(net_delta),
            tradeoff_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )
