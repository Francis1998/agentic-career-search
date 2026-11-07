# FloatingHolidayGapAdvisor Guide

![FloatingHolidayGapAdvisor HITL flow](../../assets/demo/floating-holiday-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Rippling/Gusto/BambooHR floating-holiday planners (distinct from related advisors).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `PtoAccrualCliffAdvisor` / `UnlimitedPtoUtilizationGapAdvisor`.

## Usage

```python
from autoapply_agent.services.floating_holiday_gap import FloatingHolidayGapAdvisor

report = FloatingHolidayGapAdvisor().advise(
    offered_days=100.0,
    needed_days=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
