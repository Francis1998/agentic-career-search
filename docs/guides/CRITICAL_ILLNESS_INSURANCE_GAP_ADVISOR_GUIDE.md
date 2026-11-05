# CriticalIllnessInsuranceGapAdvisor Guide

![CriticalIllnessInsuranceGapAdvisor](../../assets/demo/critical-illness-insurance-gap-advisor.gif)

Offline helper.
Gap vs Unum/Aflac/MetLife critical-illness insurance planners. Distinct from `LtdDisabilityGapAdvisor` / `LifeInsuranceCoverageGapAdvisor`.

Stack: **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.critical_illness_insurance_gap import (
    CriticalIllnessInsuranceGapAdvisor,
)

report = CriticalIllnessInsuranceGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
