# Equity Vesting Cliff Advisor Guide

![Equity vesting cliff advisor HITL flow](../../assets/demo/equity-vesting-cliff-advisor.gif)

Compute cliff + linear vesting progress for a single equity grant. Never
auto-accepts. Closes the Levels.fyi / Candor / Carta vesting-calculator gap.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `OfferCompareMatrix` and `NegotiationTalkingPointsService`.

## Usage

```python
from autoapply_agent.services.equity_vesting import EquityVestingCliffAdvisor

report = EquityVestingCliffAdvisor().advise(
    grant_value=240_000.0,
    cliff_months=12,
    vest_months=48,
    months_elapsed=18,
)
assert report.auto_accept is False
assert report.requires_human_review is True
print(report.vest_band, report.vested_value, report.unvested_value)
```

## Safety

Always `requires_human_review=True` and `auto_accept=False`. No HTTP. Humans
decide offer acceptance. See `SAFETY.md`.
