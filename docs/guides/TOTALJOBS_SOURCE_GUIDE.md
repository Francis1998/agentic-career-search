# Totaljobs Source Guide

![Totaljobs discovery flow](../../assets/demo/totaljobs-source.gif)

Use this guide when wiring a public Totaljobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Totaljobs

Totaljobs is a major UK job board covered by JobSpy-style scrapers but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "totaljobs-jobs",
    "source_type": "totaljobs",
    "base_url": "https://www.totaljobs.com/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/job/{id}` | `/job/49102` |
| `/jobs/{id}` | `/jobs/56213` |
| `/job-vacancy/{id}` | `/job-vacancy/62324` |
| `/details/{id}` | `/details/73435` |
| `/uk/job/{id}` | `/uk/job/84546` |

## Ignored paths

Board indexes (`/job`, `/jobs`, `/job-vacancy`, `/details`, `/uk/job`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-194](../adr/ADR-194-totaljobs-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
