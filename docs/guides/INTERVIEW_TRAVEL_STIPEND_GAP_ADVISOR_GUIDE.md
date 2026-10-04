# InterviewTravelStipendGapAdvisor Guide

![InterviewTravelStipendGapAdvisor HITL flow](../../assets/demo/interview-travel-stipend-gap-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Levels.fyi/Blind/Rippling interview travel stipend planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from ``CommuteCostTradeoffAdvisor` and `RemoteWorkStipendTaxGapAdvisor``.

## Usage

```python
from autoapply_agent.services.interview_travel_stipend_gap import InterviewTravelStipendGapAdvisor

report = InterviewTravelStipendGapAdvisor().advise(
    stipend_usd=800.0,
    travel_cost_usd=1200.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
