# EggFreezingBenefitGapAdvisor Guide

![EggFreezingBenefitGapAdvisor](../../assets/demo/egg-freezing-benefit-gap-advisor.gif)

Offline HITL advisor for `offered_days` vs `needed_days` coverage bands.
Gap vs Progyny/Carrot/Maven egg-freezing benefit planners. Distinct from `FertilityTravelStipendGapAdvisor` / `GenderAffirmingCareGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.egg_freezing_benefit_gap import EggFreezingBenefitGapAdvisor

report = EggFreezingBenefitGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-approves. Humans decide.
