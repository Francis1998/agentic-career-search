# AdoptionAssistanceGapAdvisor Guide

![AdoptionAssistanceGapAdvisor HITL flow](../../assets/demo/adoption-assistance-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Carrot/Progyny/Maven/Levels.fyi adoption-assistance planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `FertilityBenefitGapAdvisor` and `ParentalLeaveGapAdvisor`.

## Usage

```python
from autoapply_agent.services.adoption_assistance_gap import AdoptionAssistanceGapAdvisor

report = AdoptionAssistanceGapAdvisor().advise(
    adoption_cost_budget_usd=1800.0,
    employer_assistance_usd=1200.0,
    planned_claim_usd=1200.0,
)
assert report.auto_claim is False
assert report.requires_human_review is True
print(report.coverage_band, report.remaining_cap_usd)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
