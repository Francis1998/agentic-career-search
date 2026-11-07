# NeonatalIcuLeaveGapAdvisor Guide

![NeonatalIcuLeaveGapAdvisor](../../assets/demo/neonatal-icu-leave-gap-advisor.gif)

Offline helper.
Gap vs Rippling/Workday/Lattice neonatal-ICU parental leave planners. Distinct from `ParentalBondingLeaveGapAdvisor` / `ParentalLeaveGapAdvisor`.

Stack: **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.neonatal_icu_leave_gap import (
    NeonatalIcuLeaveGapAdvisor,
)

report = NeonatalIcuLeaveGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
