# TheMuse Source Guide

![TheMuse discovery flow](../../assets/demo/themuse-source.gif)

Use this guide when wiring a public TheMuse careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why TheMuse

The Muse is a popular career/content job board missing from many open-source scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "themuse-jobs",
    "source_type": "themuse",
    "base_url": "https://www.themuse.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/{id}` |
| Job | `/job/{id}` |
| Positions | `/positions/{id}` |
| Openings | `/openings/{id}` |
| Roles | `/roles/{id}` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
