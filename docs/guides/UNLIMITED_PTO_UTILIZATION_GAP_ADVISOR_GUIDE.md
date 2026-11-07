# UnlimitedPtoUtilizationGapAdvisor Guide

![UnlimitedPtoUtilizationGapAdvisor HITL flow](../../assets/demo/unlimited-pto-utilization-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Levels.fyi/Blind/Rippling unlimited-PTO utilization planners (distinct from related advisors).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `PtoAccrualCliffAdvisor` / `PtoCarryoverCapGapAdvisor`.

## Usage

```python
from autoapply_agent.services.unlimited_pto_utilization_gap import UnlimitedPtoUtilizationGapAdvisor

report = UnlimitedPtoUtilizationGapAdvisor().advise(
    days_taken=100.0,
    peer_median_days=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
