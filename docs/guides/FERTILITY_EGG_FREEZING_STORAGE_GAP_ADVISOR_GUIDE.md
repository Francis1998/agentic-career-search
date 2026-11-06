# FertilityEggFreezingStorageGapAdvisor Guide

![FertilityEggFreezingStorageGapAdvisor](../../assets/demo/fertility-egg-freezing-storage-gap-advisor.gif)

Offline helper.
Gap vs Carrot/Progyny/Maven egg-freezing annual storage-fee planners. Distinct from `FertilityIvfCycleGapAdvisor` / `FertilityBenefitGapAdvisor`.

Stack: **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.fertility_egg_freezing_storage_gap import (
    FertilityEggFreezingStorageGapAdvisor,
)

report = FertilityEggFreezingStorageGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
