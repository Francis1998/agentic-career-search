# WellnessStipendGapAdvisor Guide

![WellnessStipendGapAdvisor HITL flow](../../assets/demo/wellness-stipend-gap-advisor.gif)

Offline HITL advisor. Never auto-claims. Closes closed-UI gaps vs Ladder / Wellhub / Levels.fyi / Blind wellness-stipend planners.

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `HomeOfficeStipendGapAdvisor` and `OnCallStipendGapAdvisor`.

## Usage

```python
from autoapply_agent.services.wellness_stipend_gap import WellnessStipendGapAdvisor

report = WellnessStipendGapAdvisor().advise(
    annual_wellness_spend_usd=1500.0,
    employer_stipend_usd=1000.0,
    planned_claim_usd=1000.0,
)
assert report.auto_claim is False
assert report.requires_human_review is True
print(report.coverage_band, report.remaining_cap_usd)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
