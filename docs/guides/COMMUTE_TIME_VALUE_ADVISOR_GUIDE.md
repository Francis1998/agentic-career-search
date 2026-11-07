# CommuteTimeValueAdvisor Guide

![CommuteTimeValueAdvisor HITL flow](../../assets/demo/commute-time-value-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Remotive/Levels.fyi/Blind commute time-value planners (distinct from dollar commute-cost tradeoff).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `CommuteCostTradeoffAdvisor` and `TransitCommuteBenefitGapAdvisor`.

## Usage

```python
from autoapply_agent.services.commute_time_value import CommuteTimeValueAdvisor

report = CommuteTimeValueAdvisor().advise(
    weekly_commute_hours=8.0,
    hourly_opportunity_cost=40.0,
)
assert report.auto_enroll is False
print(report.coverage_band, report.weekly_time_value)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
