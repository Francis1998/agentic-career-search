# Application Stage Tracker Guide

![Application stage tracker](../../assets/demo/application-stage-tracker.gif)

Track applications through a **CRM-lite pipeline**:
`saved → applied → interview → offer → accepted|rejected`.

v1 is an in-process state machine with explicit allowed transitions. Durable DB
persistence can come later; this module keeps agent loops able to reason about
pipeline stage without auto-submitting applications.

Optional LLM notes polish can later use GPT-5.5 / Claude Sonnet 4.6 /
Gemini 3.x / Kimi K2. Stage transitions themselves stay deterministic.

## Why this exists

Teal’s pipeline is the core UX for serious job seekers. JobSpy scrapes boards
without a stage CRM. OpenHands can act on the web, which is the wrong default
for application state. This tracker fills the gap with an auditable stage
machine that agents and humans can share.

## Track a job

```python
from autoapply_agent.services.application_stages import (
    ApplicationStage,
    ApplicationStageTracker,
)

tracker = ApplicationStageTracker()
tracker.upsert("https://example.com/jobs/1", ApplicationStage.SAVED)
tracker.advance("https://example.com/jobs/1")  # → applied
tracker.upsert(
    "https://example.com/jobs/1",
    ApplicationStage.REJECTED,
    note="no reply after 14d",
)
print(tracker.list_by_stage(ApplicationStage.REJECTED))
```

## Stages and transitions

| From | Allowed next |
|---|---|
| saved | applied, rejected |
| applied | interview, rejected |
| interview | offer, rejected |
| offer | accepted, rejected |
| accepted / rejected | (terminal) |

## Safety notes

- Tracker never submits applications or contacts employers.
- Notes may contain personal data — keep them local / redacted in logs.
- v1 is in-memory; do not treat it as durable storage yet.

See `SAFETY.md` for project-wide boundaries.
