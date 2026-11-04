# RemoteStipendClawbackGapAdvisor Guide

![RemoteStipendClawbackGapAdvisor](../../assets/demo/remote-stipend-clawback-gap-advisor.gif)

Offline helper.
Gap vs Deel/Remote.com/Rippling remote stipend clawback planners. Distinct from `HomeOfficeStipendGapAdvisor` / `RelocationPackageGapAdvisor`.

Stack: **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.remote_stipend_clawback_gap import (
    RemoteStipendClawbackGapAdvisor,
)

report = RemoteStipendClawbackGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
