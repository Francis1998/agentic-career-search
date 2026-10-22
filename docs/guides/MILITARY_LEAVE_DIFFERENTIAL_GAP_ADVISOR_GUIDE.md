# MilitaryLeaveDifferentialGapAdvisor Guide

![MilitaryLeaveDifferentialGapAdvisor](../../assets/demo/military-leave-differential-gap-advisor.gif)

Offline HITL helper for `offered_days` bands.
Gap vs Rippling/Workday/BambooHR military-leave differential planners. Distinct from `JuryDutyPayGapAdvisor` / `OrganDonorLeaveGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.military_leave_differential_gap import (
    MilitaryLeaveDifferentialGapAdvisor,
)

report = MilitaryLeaveDifferentialGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
