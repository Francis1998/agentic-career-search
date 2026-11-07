# PtoAccrualCliffAdvisor Guide

![PtoAccrualCliffAdvisor HITL flow](../../assets/demo/pto-accrual-cliff-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Rippling/Gusto/Levels.fyi PTO accrual-cliff planners (distinct from PTO cash-out value).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `PtoCashOutValueAdvisor` and `SabbaticalEligibilityAdvisor`.

## Usage

```python
from autoapply_agent.services.pto_accrual_cliff import PtoAccrualCliffAdvisor

report = PtoAccrualCliffAdvisor().advise(
    accrued_hours=90.0,
    cliff_hours=80.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
