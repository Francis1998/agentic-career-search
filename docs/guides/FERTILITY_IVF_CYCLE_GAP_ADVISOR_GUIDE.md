# FertilityIvfCycleGapAdvisor Guide

![FertilityIvfCycleGapAdvisor](../../assets/demo/fertility-ivf-cycle-gap-advisor.gif)

Offline HITL helper for `offered_usd` bands.
Gap vs Carrot/Progyny/Maven IVF cycle-coverage planners. Distinct from `FertilityBenefitGapAdvisor` / `FertilityMedicationCoverageGapAdvisor`.

Optional polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.fertility_ivf_cycle_gap import (
    FertilityIvfCycleGapAdvisor,
)

report = FertilityIvfCycleGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
