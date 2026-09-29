# PetInsuranceGapAdvisor Guide

![PetInsuranceGapAdvisor HITL flow](../../assets/demo/pet-insurance-gap-advisor.gif)

Offline HITL advisor. Never auto-claims. Closes closed-UI gaps vs Figo / Trupanion / Levels.fyi / Blind pet-insurance planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `HomeOfficeStipendGapAdvisor` and `FertilityBenefitGapAdvisor`.

## Usage

```python
from autoapply_agent.services.pet_insurance_gap import PetInsuranceGapAdvisor

report = PetInsuranceGapAdvisor().advise(
    annual_vet_cost_usd=1800.0,
    employer_stipend_usd=1200.0,
    planned_claim_usd=1200.0,
)
assert report.auto_claim is False
assert report.requires_human_review is True
print(report.coverage_band, report.remaining_cap_usd)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
