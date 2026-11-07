# EquityForfeitureOnPipGapAdvisor Guide

![EquityForfeitureOnPipGapAdvisor HITL flow](../../assets/demo/equity-forfeiture-on-pip-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Carta/Pulley/Levels.fyi equity forfeiture-on-PIP planners (distinct from related advisors).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `EquityVestingCliffAdvisor` / `EquityBlackoutWindowAdvisor`.

## Usage

```python
from autoapply_agent.services.equity_forfeiture_on_pip_gap import EquityForfeitureOnPipGapAdvisor

report = EquityForfeitureOnPipGapAdvisor().advise(
    protected_equity_usd=100.0,
    unvested_equity_usd=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
