# SummerFridayGapAdvisor Guide

![SummerFridayGapAdvisor HITL flow](../../assets/demo/summer-friday-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Levels.fyi/Blind/Rippling summer-Friday planners (distinct from related advisors).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `UnlimitedPtoUtilizationGapAdvisor` / `PtoCarryoverCapGapAdvisor`.

## Usage

```python
from autoapply_agent.services.summer_friday_gap import SummerFridayGapAdvisor

report = SummerFridayGapAdvisor().advise(
    offered_fridays=100.0,
    peer_median_fridays=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
