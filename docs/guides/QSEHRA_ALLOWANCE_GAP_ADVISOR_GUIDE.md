# QsehraAllowanceGapAdvisor Guide

![QsehraAllowanceGapAdvisor](../../assets/demo/qsehra-allowance-gap-advisor.gif)

Offline helper.
Gap vs Take Command/PeopleKeep/WiserAdvise QSEHRA allowance planners. Distinct from `HsaEmployerSeedGapAdvisor` / `HsaContributionGapAdvisor`.

Stack: **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.qsehra_allowance_gap import (
    QsehraAllowanceGapAdvisor,
)

report = QsehraAllowanceGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
