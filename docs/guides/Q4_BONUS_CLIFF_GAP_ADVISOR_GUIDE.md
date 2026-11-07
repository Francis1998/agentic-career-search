# Q4BonusCliffGapAdvisor Guide

![Q4BonusCliffGapAdvisor](../../assets/demo/q4-bonus-cliff-gap-advisor.gif)

Offline helper.
Gap vs Rippling/Lattice/BambooHR Q4 bonus-cliff planners. Distinct from `RetentionBonusCliffAdvisor` / `YearEndBonusProrataGapAdvisor`.

Stack: **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.q4_bonus_cliff_gap import (
    Q4BonusCliffGapAdvisor,
)

report = Q4BonusCliffGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
