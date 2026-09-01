# Jooble Source Guide

![Jooble discovery flow](../../assets/demo/jooble-source.gif)

Use this guide when wiring a public Jooble careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Jooble

Jooble is a widely used international job aggregator missing from many open-source scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "jooble-jobs",
    "source_type": "jooble",
    "base_url": "https://jooble.org/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/49102` |
| Job | `/job/56213` |
| Vacancy | `/vacancy/62324` |
| Vacancies | `/vacancies/73435` |
| Listings | `/listings/84546` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
