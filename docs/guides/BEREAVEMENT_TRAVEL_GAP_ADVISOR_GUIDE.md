# BereavementTravelGapAdvisor Guide

![BereavementTravelGapAdvisor](../../assets/demo/bereavement-travel-gap-advisor.gif)

Offline HITL helper for `offered_usd` bands.
Gap vs Rippling/Workday/BambooHR bereavement-travel stipend planners. Distinct from `BereavementLeaveGapAdvisor` / `PetBereavementLeaveGapAdvisor`.

Optional polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.bereavement_travel_gap import (
    BereavementTravelGapAdvisor,
)

report = BereavementTravelGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
