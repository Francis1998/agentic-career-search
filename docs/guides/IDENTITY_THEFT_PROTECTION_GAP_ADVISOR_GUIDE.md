# IdentityTheftProtectionGapAdvisor Guide

![IdentityTheftProtectionGapAdvisor HITL flow](../../assets/demo/identity-theft-protection-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Norton/LifeLock/Aura/Levels.fyi identity-theft benefit planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `WellnessStipendGapAdvisor` and `PetInsuranceGapAdvisor`.

## Usage

```python
from autoapply_agent.services.identity_theft_protection_gap import IdentityTheftProtectionGapAdvisor

report = IdentityTheftProtectionGapAdvisor().advise(
    household_risk_budget_usd=1800.0,
    employer_benefit_usd=1200.0,
    planned_claim_usd=1200.0,
)
assert report.auto_claim is False
assert report.requires_human_review is True
print(report.coverage_band, report.remaining_cap_usd)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
