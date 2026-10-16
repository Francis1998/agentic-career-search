# ConferenceBudgetGapAdvisor Guide

![ConferenceBudgetGapAdvisor HITL flow](../../assets/demo/conference-budget-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Rippling/Culture Amp/Lattice conference-budget planners (distinct from related advisors).

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `TuitionReimbursementGapAdvisor` / `WellnessStipendGapAdvisor`.

## Usage

```python
from autoapply_agent.services.conference_budget_gap import ConferenceBudgetGapAdvisor

report = ConferenceBudgetGapAdvisor().advise(
    offered_budget_usd=100.0,
    needed_budget_usd=100.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
