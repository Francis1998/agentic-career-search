# VisionInsuranceBuyupGapAdvisor Guide

![VisionInsuranceBuyupGapAdvisor](../../assets/demo/vision-insurance-buyup-gap-advisor.gif)

Offline helper.
Gap vs VSP/EyeMed/Davis Vision buy-up allowance planners. Distinct from `DisabilityInsuranceBuyupGapAdvisor` / `LifeInsuranceCoverageGapAdvisor`.

Stack: **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.vision_insurance_buyup_gap import (
    VisionInsuranceBuyupGapAdvisor,
)

report = VisionInsuranceBuyupGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
