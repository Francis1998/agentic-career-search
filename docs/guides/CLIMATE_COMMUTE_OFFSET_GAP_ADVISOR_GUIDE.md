# ClimateCommuteOffsetGapAdvisor Guide

![ClimateCommuteOffsetGapAdvisor](../../assets/demo/climate-commute-offset-gap-advisor.gif)

Offline helper.
Gap vs Watershed/Normative/Sweep climate commute-carbon offset planners. Distinct from `ClimateResilienceLeaveGapAdvisor` / `TransitCommuteBenefitGapAdvisor`.

Stack: **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.climate_commute_offset_gap import (
    ClimateCommuteOffsetGapAdvisor,
)

report = ClimateCommuteOffsetGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
