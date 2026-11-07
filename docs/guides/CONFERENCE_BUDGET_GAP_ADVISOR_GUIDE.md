# ConferenceBudgetGapAdvisor Guide

![ConferenceBudgetGapAdvisor HITL flow](../../assets/demo/conference-budget-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Rippling/Culture Amp/Lattice conference-budget planners (distinct from related advisors).

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

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
