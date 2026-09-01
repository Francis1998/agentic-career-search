# SimplyHired Source Guide

![SimplyHired discovery flow](../../assets/demo/simplyhired-source.gif)

Use this guide when wiring a public SimplyHired careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why SimplyHired

SimplyHired remains a popular aggregator gap alongside Indeed/ZipRecruiter in JobSpy-style stacks; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "simplyhired-jobs",
    "source_type": "simplyhired",
    "base_url": "https://www.simplyhired.com/search"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Job | `/job/49102` |
| Jobs | `/jobs/56213` |
| Listings | `/listings/62324` |
| Positions | `/positions/73435` |
| Openings | `/openings/84546` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
