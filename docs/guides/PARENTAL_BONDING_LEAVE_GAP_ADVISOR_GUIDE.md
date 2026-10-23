# ParentalBondingLeaveGapAdvisor Guide

![ParentalBondingLeaveGapAdvisor](../../assets/demo/parental-bonding-leave-gap-advisor.gif)

Offline HITL helper for `offered_days` bands.
Gap vs Rippling/Workday/BambooHR parental bonding-leave planners. Distinct from `ParentalLeaveGapAdvisor` / `CaregiverBackupCareGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.parental_bonding_leave_gap import ParentalBondingLeaveGapAdvisor

report = ParentalBondingLeaveGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
