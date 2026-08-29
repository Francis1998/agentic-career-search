# AI Jobs Source Guide

![AI Jobs discovery flow](../../assets/demo/aijobs-source.gif)

Use this guide when wiring a public AI Jobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why AI Jobs

AI Jobs (ai-jobs.net) covers ML/LLM roles that generic remote boards miss; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "aijobs-jobs",
    "source_type": "aijobs",
    "base_url": "https://ai-jobs.net/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Ai Jobs | `/ai-jobs/49102` |
| Roles | `/roles/56213` |
| Openings | `/openings/62324` |
| Jobs | `/jobs/73435` |
| Job | `/job/84546` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
