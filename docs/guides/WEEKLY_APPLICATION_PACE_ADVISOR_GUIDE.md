# Weekly Application Pace Advisor Guide

![Weekly application pace advisor HITL flow](../../assets/demo/weekly-application-pace-advisor.gif)

Generate deterministic, offline **weekly application pace bands and HITL
guidance**. Never auto-submits. Closes the gap vs Teal Insights / Huntr
analytics dashboards that keep apply-volume coaching inside proprietary UIs.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.
The pace math itself stays deterministic.

## Why this exists

Spray-and-pray apply volume burns candidates out. Closed job trackers show
charts, but few open-source career agents expose a local pace advisor with
explicit bands and human-review guidance. This service always sets
`requires_human_review=True`, keeps `auto_submit=False`, and performs no
network I/O.

## Usage

```python
from autoapply_agent.services.weekly_pace import WeeklyApplicationPaceAdvisor

advice = WeeklyApplicationPaceAdvisor().advise(
    week_label="2026-W37",
    planned_applications=18,
    target_applications=10,
)
assert advice.requires_human_review is True
assert advice.auto_submit is False
print(advice.band, advice.pace_ratio)
print(advice.guidance)
```

Bands: `under_pace` (<0.5), `on_pace` (0.5–1.25), `hot` (1.25–1.75),
`overload` (>1.75).

## Safety

Always `requires_human_review=True` and `auto_submit=False`. No HTTP. Humans
decide how many applications to send. See `SAFETY.md`.
