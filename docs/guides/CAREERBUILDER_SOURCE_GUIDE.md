# CareerBuilder Source Guide

![CareerBuilder discovery flow](../../assets/demo/careerbuilder-source.gif)

Use this guide when wiring a public CareerBuilder careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why CareerBuilder

CareerBuilder is a major US job board present in JobSpy-style aggregators but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "careerbuilder-jobs",
    "source_type": "careerbuilder",
    "base_url": "https://www.careerbuilder.com/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/job/{id}` | `/job/49102` |
| `/jobs/{id}` | `/jobs/56213` |
| `/jobseeker/jobs/{id}` | `/jobseeker/jobs/62324` |
| `/share/job/{id}` | `/share/job/73435` |
| `/career-jobs/{id}` | `/career-jobs/84546` |

## Ignored paths

Board indexes (`/job`, `/jobs`, `/jobseeker/jobs`, `/share/job`, `/career-jobs`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-190](../adr/ADR-190-careerbuilder-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
