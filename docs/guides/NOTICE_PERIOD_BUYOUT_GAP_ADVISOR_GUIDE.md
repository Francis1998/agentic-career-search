# NoticePeriodBuyoutGapAdvisor Guide

![NoticePeriodBuyoutGapAdvisor HITL flow](../../assets/demo/notice-period-buyout-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Clerky/Blind/Levels.fyi notice-period buyout planners (distinct from related advisors).

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `GardenLeaveGapAdvisor` and `SeverancePackageGapAdvisor`.

## Usage

```python
from autoapply_agent.services.notice_period_buyout_gap import NoticePeriodBuyoutGapAdvisor

report = NoticePeriodBuyoutGapAdvisor().advise(
    buyout_weeks=100.0,
    needed_weeks=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
