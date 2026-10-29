# EsppContributionGapAdvisor Guide

![EsppContributionGapAdvisor](../../assets/demo/espp-contribution-gap-advisor.gif)

Offline HITL helper for `offered_pct` bands.
Gap vs Carta/Shareworks/E*TRADE ESPP contribution planners. Distinct from `EsppLookbackGapAdvisor` / `RsuSupplementalWithholdingGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.espp_contribution_gap import EsppContributionGapAdvisor

report = EsppContributionGapAdvisor().advise(
    offered_pct=50.0,
    needed_pct=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
