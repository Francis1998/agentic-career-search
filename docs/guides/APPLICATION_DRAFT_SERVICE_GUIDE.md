# Application Draft Service Guide

![Application draft HITL flow](../../assets/demo/application-draft-hitl.gif)

Generate **human-reviewed** resume bullets and a short cover note from a job
title, company, and optional search query. Drafts are deterministic templates —
they never submit applications over HTTP.

Optional LLM polish can later use GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x /
Kimi K2. The draft generator itself stays network-free and SAFETY-aligned.

## Why this exists

Teal and Simplify help users tailor materials, but they are UI-centric and not
wired into an autonomous discovery agent. JobSpy scrapes boards without draft
assist. OpenHands-style agents can browse and act, which is the wrong default
for apply flows. This service fills the gap with **HITL-only** draft packages.

## Generate a draft

```python
from autoapply_agent.services.application_drafts import ApplicationDraftService

draft = ApplicationDraftService().generate(
    job_title="Senior Backend Engineer",
    company="Acme Labs",
    query="python fastapi",
)

assert draft.requires_human_review is True
assert draft.auto_submit is False
print(draft.resume_bullets)
print(draft.cover_note)
```

## What you get

| Field | Purpose |
|---|---|
| `resume_bullets` | 4 deterministic bullet suggestions |
| `cover_note` | Short editable cover-note template |
| `requires_human_review` | Always `True` |
| `auto_submit` | Always `False` |

## Safety notes

- No HTTP apply, form POST, or credential automation.
- Output is a draft package for human editing before any submission.
- Keep secrets out of draft text; treat drafts as local assistive content.

See `SAFETY.md` for project-wide boundaries.
