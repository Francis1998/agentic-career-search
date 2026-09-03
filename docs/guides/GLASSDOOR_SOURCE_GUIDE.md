# Glassdoor Source Guide

![Glassdoor discovery flow](../../assets/demo/glassdoor-source.gif)

Use this guide when wiring a public Glassdoor careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Glassdoor

Glassdoor is a widely-used employer review and job board missing from many open-source scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "glassdoor-jobs",
    "source_type": "glassdoor",
    "base_url": "https://www.glassdoor.com/Job/jobs.htm",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/reviews/{id}` | `/reviews/49102` |
| `/jobs/{id}` | `/jobs/56213` |
| `/job-listing/{id}` | `/job-listing/62324` |
| `/positions/{id}` | `/positions/73435` |
| `/openings/{id}` | `/openings/84546` |

## Ignored paths

Board indexes (`/reviews`, `/jobs`, `/job-listing`, `/positions`, `/openings`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-186](../adr/ADR-186-glassdoor-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
