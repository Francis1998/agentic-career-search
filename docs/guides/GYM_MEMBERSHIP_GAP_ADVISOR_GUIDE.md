# GymMembershipGapAdvisor Guide

![GymMembershipGapAdvisor](../../assets/demo/gym-membership-gap-advisor.gif)

Offline HITL advisor for `offered_usd` vs `needed_usd` coverage bands.
Gap vs Rippling/WellnessLiving/Levels.fyi gym-membership planners. Distinct from `MealStipendGapAdvisor` / `HomeOfficeStipendGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.gym_membership_gap import GymMembershipGapAdvisor

report = GymMembershipGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-enrolls. Humans decide.
