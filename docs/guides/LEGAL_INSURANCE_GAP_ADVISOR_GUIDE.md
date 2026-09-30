# LegalInsuranceGapAdvisor Guide

![LegalInsuranceGapAdvisor HITL flow](../../assets/demo/legal-insurance-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs LegalShield/ARAG/Levels.fyi/Blind legal-plan planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `PetInsuranceGapAdvisor` and `DependentCareFsaGapAdvisor`.

## Usage

```python
from autoapply_agent.services.legal_insurance_gap import LegalInsuranceGapAdvisor

report = LegalInsuranceGapAdvisor().advise(
    annual_legal_need_usd=1800.0,
    employer_plan_value_usd=1200.0,
    planned_use_usd=1200.0,
)
assert report.auto_claim is False
assert report.requires_human_review is True
print(report.coverage_band, report.remaining_cap_usd)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
