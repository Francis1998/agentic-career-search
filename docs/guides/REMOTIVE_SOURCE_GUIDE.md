# Remotive Source Guide

![Remotive discovery flow](../../assets/demo/remotive-source.gif)

Use this guide when wiring a public Remotive careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Remotive

Remotive publishes remote job boards whose public listings commonly link to
detail pages under /remote-jobs/{id}, /remote-job/{id}, /jobs/{id}, /job/{id},
or /positions/{id}. ATS-focused adapters leave Remotive aggregator boards
without deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "remotive-remote",
    "source_type": "remotive",
    "base_url": "https://remotive.com/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Remote Jobs | `/remote-jobs/48291` |
| Remote Job | `/remote-job/55902` |
| Jobs | `/jobs/61033` |
| Job | `/job/72044` |
| Positions | `/positions/83155` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
