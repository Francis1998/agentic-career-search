# IpoLockupReleaseGapAdvisor Guide

![IpoLockupReleaseGapAdvisor HITL flow](../../assets/demo/ipo-lockup-release-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Carta/Pulley/Levels.fyi IPO lockup-release planners (distinct from related advisors).

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `EquityBlackoutWindowAdvisor` / `StockOptionExerciseWindowAdvisor`.

## Usage

```python
from autoapply_agent.services.ipo_lockup_release_gap import IpoLockupReleaseGapAdvisor

report = IpoLockupReleaseGapAdvisor().advise(
    days_to_lockup_end=100.0,
    needed_liquidity_days=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
