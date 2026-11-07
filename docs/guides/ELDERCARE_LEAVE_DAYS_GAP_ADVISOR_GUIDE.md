# EldercareLeaveDaysGapAdvisor Guide

![EldercareLeaveDaysGapAdvisor HITL flow](../../assets/demo/eldercare-leave-days-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Lattice/Rippling/Justworks eldercare leave planners.

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `ParentalLeaveGapAdvisor` and `PaidFamilyLeaveStateGapAdvisor`.

## Usage

```python
from autoapply_agent.services.eldercare_leave_days_gap import EldercareLeaveDaysGapAdvisor

report = EldercareLeaveDaysGapAdvisor().advise(
    offered_days=80.0,
    needed_days=50.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
