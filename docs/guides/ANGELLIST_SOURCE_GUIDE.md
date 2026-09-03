# AngelList Source Guide

![AngelList discovery flow](../../assets/demo/angellist-source.gif)

Use this guide when wiring a public AngelList (Wellfound) careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why AngelList

AngelList (Wellfound) is a prominent startup job board missing from many open-source scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "angellist-jobs",
    "source_type": "angellist",
    "base_url": "https://angel.co/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/jobs/{id}` | `/jobs/49102` |
| `/startups/{id}` | `/startups/56213` |
| `/startup-jobs/{id}` | `/startup-jobs/62324` |
| `/roles/{id}` | `/roles/73435` |
| `/positions/{id}` | `/positions/84546` |

## Ignored paths

Board indexes (`/jobs`, `/startups`, `/startup-jobs`, `/roles`, `/positions`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-187](../adr/ADR-187-angellist-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
