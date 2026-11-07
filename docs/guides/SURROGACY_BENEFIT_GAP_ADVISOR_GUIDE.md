# SurrogacyBenefitGapAdvisor Guide

![SurrogacyBenefitGapAdvisor](../../assets/demo/surrogacy-benefit-gap-advisor.gif)

Offline HITL helper for `offered_days` bands.
Gap vs Carrot/Progyny/Kindbody surrogacy benefit planners. Distinct from `EggFreezingBenefitGapAdvisor` / `FertilityTravelStipendGapAdvisor`.

Optional polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

## Usage

```python
from autoapply_agent.services.surrogacy_benefit_gap import SurrogacyBenefitGapAdvisor

report = SurrogacyBenefitGapAdvisor().advise(
    offered_days=50.0,
    needed_days=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
