# ParkingStipendGapAdvisor Guide

![ParkingStipendGapAdvisor HITL flow](../../assets/demo/parking-stipend-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Rippling/Gusto/Levels.fyi parking-stipend planners (distinct from related advisors).

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `TransitCommuteBenefitGapAdvisor` / `CommuteCostTradeoffAdvisor`.

## Usage

```python
from autoapply_agent.services.parking_stipend_gap import ParkingStipendGapAdvisor

report = ParkingStipendGapAdvisor().advise(
    offered_parking_usd=100.0,
    needed_parking_usd=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
