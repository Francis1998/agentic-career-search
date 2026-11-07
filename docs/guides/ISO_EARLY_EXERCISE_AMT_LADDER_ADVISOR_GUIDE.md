# IsoEarlyExerciseAmtLadderAdvisor Guide

![IsoEarlyExerciseAmtLadderAdvisor HITL flow](../../assets/demo/iso-early-exercise-amt-ladder-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Carta/Pulley/Levels.fyi ISO early-exercise AMT ladder planners (distinct from related advisors).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `IsoAmtExposureAdvisor` (bargain-element snapshot) / `EsppLookbackGapAdvisor`.

## Usage

```python
from autoapply_agent.services.iso_early_exercise_amt_ladder import IsoEarlyExerciseAmtLadderAdvisor

report = IsoEarlyExerciseAmtLadderAdvisor().advise(
    ladder_years=100.0,
    needed_years=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
