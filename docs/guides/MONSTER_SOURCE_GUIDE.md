# Monster Source Guide

![Monster discovery flow](../../assets/demo/monster-source.gif)

Use this guide when wiring a public Monster careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Monster

Monster is a widely-used aggregator job board covered by JobSpy-style scrapers but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "monster-jobs",
    "source_type": "monster",
    "base_url": "https://www.monster.com/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/jobs/job/{id}` | `/jobs/job/49102` |
| `/job-openings/{id}` | `/job-openings/56213` |
| `/jobs/{id}` | `/jobs/62324` |
| `/career/{id}` | `/career/73435` |
| `/m/job/{id}` | `/m/job/84546` |

## Ignored paths

Board indexes (`/jobs/job`, `/job-openings`, `/jobs`, `/career`, `/m/job`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-189](../adr/ADR-189-monster-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
