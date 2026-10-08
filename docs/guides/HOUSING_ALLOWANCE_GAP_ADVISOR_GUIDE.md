# HousingAllowanceGapAdvisor Guide

![HousingAllowanceGapAdvisor HITL flow](../../assets/demo/housing-allowance-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs NerdWallet/Levels.fyi/Blind housing allowance planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `ColAdjustedOfferAdvisor` and `RelocationPackageGapAdvisor`.

## Usage

```python
from autoapply_agent.services.housing_allowance_gap import HousingAllowanceGapAdvisor

report = HousingAllowanceGapAdvisor().advise(
    allowance_usd=80.0,
    monthly_housing_cost_usd=50.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
