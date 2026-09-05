# Naukri Source Guide

![Naukri discovery flow](../../assets/demo/naukri-source.gif)

Use this guide when wiring a public Naukri careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Naukri

Naukri is India's largest job board covered by JobSpy-style scrapers but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "naukri-jobs",
    "source_type": "naukri",
    "base_url": "https://www.naukri.com/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/job-listings/{id}` | `/job-listings/49102` |
| `/jobdetail/{id}` | `/jobdetail/56213` |
| `/jobs/{id}` | `/jobs/62324` |
| `/job-description/{id}` | `/job-description/73435` |
| `/recruiters/job/{id}` | `/recruiters/job/84546` |

## Ignored paths

Board indexes (`/job-listings`, `/jobdetail`, `/jobs`, `/job-description`, `/recruiters/job`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-193](../adr/ADR-193-naukri-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
