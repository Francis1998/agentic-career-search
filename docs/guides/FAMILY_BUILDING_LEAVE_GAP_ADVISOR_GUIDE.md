# FamilyBuildingLeaveGapAdvisor Guide

![FamilyBuildingLeaveGapAdvisor](../../assets/demo/family-building-leave-gap-advisor.gif)

Offline HITL helper for `offered_days` bands.
Gap vs Carrot/Progyny/Maven family-building leave planners. Distinct from `FertilityBenefitGapAdvisor` / `SurrogacyBenefitGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.family_building_leave_gap import FamilyBuildingLeaveGapAdvisor

report = FamilyBuildingLeaveGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
