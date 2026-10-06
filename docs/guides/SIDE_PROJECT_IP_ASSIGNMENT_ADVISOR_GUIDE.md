# SideProjectIpAssignmentAdvisor Guide

![SideProjectIpAssignmentAdvisor HITL flow](../../assets/demo/side-project-ip-assignment-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Clerky/Carta/Blind side-project IP assignment planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `StockOptionExerciseWindowAdvisor` and `ChangeOfControlAccelerationAdvisor`.

## Usage

```python
from autoapply_agent.services.side_project_ip_assignment import SideProjectIpAssignmentAdvisor

report = SideProjectIpAssignmentAdvisor().advise(
    retained_ip_pct=80.0,
    target_retain_pct=50.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
