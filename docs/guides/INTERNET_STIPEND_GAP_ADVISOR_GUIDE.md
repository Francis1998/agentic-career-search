# InternetStipendGapAdvisor Guide

![InternetStipendGapAdvisor](../../assets/demo/internet-stipend-gap-advisor.gif)

Offline HITL helper for `offered_usd` bands.
Gap vs Rippling/Deel/Remote.com internet stipend planners. Distinct from `HomeOfficeStipendGapAdvisor` / `CommuteStipendGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.internet_stipend_gap import InternetStipendGapAdvisor

report = InternetStipendGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
