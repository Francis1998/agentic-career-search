# SeveranceCobraTopupGapAdvisor Guide

![SeveranceCobraTopupGapAdvisor HITL flow](../../assets/demo/severance-cobra-topup-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs NerdWallet/Levels.fyi/Blind severance COBRA top-up planners (distinct from related advisors).

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `CobraContinuationGapAdvisor` and `SeverancePackageGapAdvisor`.

## Usage

```python
from autoapply_agent.services.severance_cobra_topup_gap import SeveranceCobraTopupGapAdvisor

report = SeveranceCobraTopupGapAdvisor().advise(
    topup_months=100.0,
    needed_months=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
