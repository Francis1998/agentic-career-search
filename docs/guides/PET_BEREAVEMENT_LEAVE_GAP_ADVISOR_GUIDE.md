# PetBereavementLeaveGapAdvisor Guide

![PetBereavementLeaveGapAdvisor](../../assets/demo/pet-bereavement-leave-gap-advisor.gif)

Offline HITL advisor for `offered_days` vs `needed_days` coverage bands.
Gap vs Lattice/Rippling/BambooHR pet-bereavement leave planners. Distinct from `BereavementLeaveGapAdvisor` / `EldercareLeaveDaysGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.pet_bereavement_leave_gap import PetBereavementLeaveGapAdvisor

report = PetBereavementLeaveGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-approves. Humans decide.
