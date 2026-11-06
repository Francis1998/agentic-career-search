# CommuterStipendRolloverGapAdvisor Guide

![CommuterStipendRolloverGapAdvisor](../../assets/demo/commuter-stipend-rollover-gap-advisor.gif)

Offline helper.
Gap vs WageWorks/Edenred/CommuterBenefits.com year-end rollover planners. Distinct from `TransitCommuteBenefitGapAdvisor` / `ClimateCommuteOffsetGapAdvisor`.

Stack: **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.commuter_stipend_rollover_gap import (
    CommuterStipendRolloverGapAdvisor,
)

report = CommuterStipendRolloverGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
