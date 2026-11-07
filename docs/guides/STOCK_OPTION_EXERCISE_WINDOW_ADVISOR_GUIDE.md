# StockOptionExerciseWindowAdvisor Guide

![StockOptionExerciseWindowAdvisor HITL flow](../../assets/demo/stock-option-exercise-window-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Carta/Pulley/Levels.fyi post-termination option exercise-window planners.

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `IsoAmtExposureAdvisor` and `EquityVestingCliffAdvisor`.

## Usage

```python
from autoapply_agent.services.stock_option_exercise_window import StockOptionExerciseWindowAdvisor

report = StockOptionExerciseWindowAdvisor().advise(
    days_remaining=10.0,
    min_exercise_days=7.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
