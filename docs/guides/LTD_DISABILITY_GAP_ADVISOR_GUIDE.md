# LtdDisabilityGapAdvisor Guide

![LtdDisabilityGapAdvisor HITL flow](../../assets/demo/ltd-disability-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Unum/MetLife/Guardian/Levels.fyi LTD disability planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `IdentityTheftProtectionGapAdvisor` and `LegalInsuranceGapAdvisor`.

## Usage

```python
from autoapply_agent.services.ltd_disability_gap import LtdDisabilityGapAdvisor

report = LtdDisabilityGapAdvisor().advise(
    income_replacement_need_usd=1800.0,
    employer_ltd_benefit_usd=1200.0,
    planned_claim_usd=1200.0,
)
assert report.auto_claim is False
assert report.requires_human_review is True
print(report.coverage_band, report.remaining_cap_usd)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
