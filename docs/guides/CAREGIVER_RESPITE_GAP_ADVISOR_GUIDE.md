# CaregiverRespiteGapAdvisor Guide

![CaregiverRespiteGapAdvisor](../../assets/demo/caregiver-respite-gap-advisor.gif)

Offline HITL helper for `offered_days` bands.
Gap vs Wellthy/Cariloop/Torchlight caregiver respite planners. Distinct from `CaregiverBackupCareGapAdvisor` / `ParentalBondingLeaveGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.caregiver_respite_gap import CaregiverRespiteGapAdvisor

report = CaregiverRespiteGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
