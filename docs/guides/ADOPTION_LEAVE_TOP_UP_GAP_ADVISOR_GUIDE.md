# AdoptionLeaveTopUpGapAdvisor Guide

![AdoptionLeaveTopUpGapAdvisor](../../assets/demo/adoption-leave-top-up-gap-advisor.gif)

Offline HITL helper for `offered_days` bands.
Gap vs Rippling/Workday/BambooHR adoption leave top-up planners. Distinct from `AdoptionAssistanceGapAdvisor` / `ParentalBondingLeaveGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.adoption_leave_top_up_gap import AdoptionLeaveTopUpGapAdvisor

report = AdoptionLeaveTopUpGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
