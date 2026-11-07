# OutplacementServiceGapAdvisor Guide

![OutplacementServiceGapAdvisor](../../assets/demo/outplacement-service-gap-advisor.gif)

Offline HITL helper for `offered_days` bands.
Gap vs Right Management/RiseSmart/CareerBuilder outplacement planners. Distinct from `SeverancePackageGapAdvisor` / `SeveranceCobraTopupGapAdvisor`.

Optional polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.outplacement_service_gap import OutplacementServiceGapAdvisor

report = OutplacementServiceGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
