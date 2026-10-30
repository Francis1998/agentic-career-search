# DisabilityInsuranceBuyupGapAdvisor Guide

![DisabilityInsuranceBuyupGapAdvisor](../../assets/demo/disability-insurance-buyup-gap-advisor.gif)

Offline HITL helper for `offered_pct` bands.
Gap vs Unum/Lincoln Financial/MetLife disability insurance buy-up planners. Distinct from `LtdDisabilityGapAdvisor` / `CobraContinuationGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.disability_insurance_buyup_gap import (
    DisabilityInsuranceBuyupGapAdvisor,
)

report = DisabilityInsuranceBuyupGapAdvisor().advise(
    offered_pct=50.0,
    needed_pct=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
