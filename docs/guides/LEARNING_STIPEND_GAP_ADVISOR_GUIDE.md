# LearningStipendGapAdvisor Guide

![LearningStipendGapAdvisor](../../assets/demo/learning-stipend-gap-advisor.gif)

Offline HITL advisor for `offered_usd` vs `needed_usd` coverage bands.
Gap vs Rippling/Guild/Levels.fyi learning-stipend planners. Distinct from `MealStipendGapAdvisor` / `ConferenceBudgetGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.learning_stipend_gap import LearningStipendGapAdvisor

report = LearningStipendGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-enrolls. Humans decide.
