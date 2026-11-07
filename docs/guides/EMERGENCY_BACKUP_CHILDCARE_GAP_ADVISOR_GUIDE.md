# EmergencyBackupChildcareGapAdvisor Guide

![EmergencyBackupChildcareGapAdvisor](../../assets/demo/emergency-backup-childcare-gap-advisor.gif)

Offline helper.
Gap vs Bright Horizons/Care.com/Rippling emergency backup-childcare planners. Distinct from `ChildcareSubsidyGapAdvisor` / `ParentalBondingLeaveGapAdvisor`.

Stack: **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.emergency_backup_childcare_gap import (
    EmergencyBackupChildcareGapAdvisor,
)

report = EmergencyBackupChildcareGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
