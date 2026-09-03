# Indeed Source Guide

![Indeed discovery flow](../../assets/demo/indeed-source.gif)

Use this guide when wiring a public Indeed careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Indeed

Indeed is a widely-used aggregator job board missing from this repository's
adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "indeed-jobs",
    "source_type": "indeed",
    "base_url": "https://www.indeed.com/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/viewjob/{id}` | `/viewjob/49102` |
| `/jobs/{id}` | `/jobs/56213` |
| `/job/{id}` | `/job/62324` |
| `/rc/clk/{id}` | `/rc/clk/73435` |
| `/m/jobs/{id}` | `/m/jobs/84546` |

## Ignored paths

Board indexes (`/viewjob`, `/jobs`, `/job`, `/rc/clk`, `/m/jobs`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-188](../adr/ADR-188-indeed-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
