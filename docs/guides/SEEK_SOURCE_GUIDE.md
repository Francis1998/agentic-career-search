# Seek Source Guide

![Seek discovery flow](../../assets/demo/seek-source.gif)

Use this guide when wiring a public Seek careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Seek

Seek is the dominant ANZ job board covered by JobSpy-style scrapers but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "seek-jobs",
    "source_type": "seek",
    "base_url": "https://www.seek.com.au/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/job/{id}` | `/job/49102` |
| `/jobs/{id}` | `/jobs/56213` |
| `/listed-job/{id}` | `/listed-job/62324` |
| `/jobsearch/{id}` | `/jobsearch/73435` |
| `/au/job/{id}` | `/au/job/84546` |

## Ignored paths

Board indexes (`/job`, `/jobs`, `/listed-job`, `/jobsearch`, `/au/job`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-192](../adr/ADR-192-seek-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
