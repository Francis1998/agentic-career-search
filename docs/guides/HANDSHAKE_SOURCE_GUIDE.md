# Handshake Source Guide

![Handshake discovery flow](../../assets/demo/handshake-source.gif)

Use this guide when wiring a public Handshake careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Handshake

Handshake is the leading university career marketplace covered by modern job scrapers but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "handshake-jobs",
    "source_type": "handshake",
    "base_url": "https://joinhandshake.com/jobs",
    "max_jobs": 50
  }'
```

## Recognised URL shapes

| Prefix | Example |
|---|---|
| `/jobs/{id}` | `/jobs/49102` |
| `/job-search/{id}` | `/job-search/56213` |
| `/postings/{id}` | `/postings/62324` |
| `/edu/jobs/{id}` | `/edu/jobs/73435` |
| `/internship/{id}` | `/internship/84546` |

## Ignored paths

Board indexes (`/jobs`, `/job-search`, `/postings`, `/edu/jobs`, `/internship`),
apply/login/signin/application/about/index pages, and navigation links are
filtered out automatically.

## See also

- [ADR-191](../adr/ADR-191-handshake-source-adapter.md)
- [ADR-077](../adr/ADR-077-deterministic-html-discovery.md) (deterministic discovery policy)
