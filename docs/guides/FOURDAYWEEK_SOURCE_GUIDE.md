# 4 Day Week Source Guide

![4 Day Week discovery flow](../../assets/demo/fourdayweek-source.gif)

Use this guide when wiring a public 4 Day Week careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why 4 Day Week

4 Day Week (4dayweek.io) is a compressed-week remote board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "fourdayweek-jobs",
    "source_type": "fourdayweek",
    "base_url": "https://4dayweek.io/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Four Day | `/four-day/48291` |
| Listings | `/listings/55902` |
| Positions | `/positions/61033` |
| Jobs | `/jobs/72044` |
| Job | `/job/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
