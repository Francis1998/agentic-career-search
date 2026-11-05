# HsaEmployerSeedGapAdvisor Guide

![HsaEmployerSeedGapAdvisor](../../assets/demo/hsa-employer-seed-gap-advisor.gif)

Offline helper.
Gap vs WageWorks/Optum/Fidelity HSA employer-seed planners. Distinct from `HsaContributionGapAdvisor` / `DependentCareFsaGapAdvisor`.

Stack: **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.hsa_employer_seed_gap import (
    HsaEmployerSeedGapAdvisor,
)

report = HsaEmployerSeedGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
