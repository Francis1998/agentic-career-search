# TuitionReimbursementCapGapAdvisor Guide

![TuitionReimbursementCapGapAdvisor](../../assets/demo/tuition-reimbursement-cap-gap-advisor.gif)

Offline HITL helper for `offered_usd` bands.
Gap vs Guild/EdAssist/Workday tuition reimbursement annual-cap planners. Distinct from `TuitionReimbursementGapAdvisor` / `LearningStipendGapAdvisor`.

Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

## Usage

```python
from autoapply_agent.services.tuition_reimbursement_cap_gap import TuitionReimbursementCapGapAdvisor

report = TuitionReimbursementCapGapAdvisor().advise(
    offered_usd=50.0,
    needed_usd=100.0,
)
assert report.requires_human_review is True
assert report.auto_approve is False
print(report.coverage_band)
```

## Safety

Advisory only. No network I/O. Never auto-acts. Humans decide.
