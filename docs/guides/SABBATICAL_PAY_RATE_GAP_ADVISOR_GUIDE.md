# SabbaticalPayRateGapAdvisor Guide

![SabbaticalPayRateGapAdvisor](../../assets/demo/sabbatical-pay-rate-gap-advisor.gif)

Offline HITL helper for `offered_pct` bands.
Gap vs Lattice/Culture Amp/Workday sabbatical pay-rate planners. Distinct from `SabbaticalAccrualGapAdvisor` / `UnlimitedPtoUtilizationGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.sabbatical_pay_rate_gap import (
    SabbaticalPayRateGapAdvisor,
)

report = SabbaticalPayRateGapAdvisor().advise(
    offered_pct=50.0,
    needed_pct=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
