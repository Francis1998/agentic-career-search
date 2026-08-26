# Dynamite Jobs Source Guide

![Dynamite Jobs discovery flow](../../assets/demo/dynamitejobs-source.gif)

Use this guide when wiring a public Dynamite Jobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Dynamite Jobs

Inspired by remote job board aggregators (Himalayas/Remotive-style boards); this repo's board adapters left Dynamite Jobs without deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "dynamitejobs-jobs",
    "source_type": "dynamitejobs",
    "base_url": "https://dynamitejobs.com/remote-jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Remote Jobs | `/remote-jobs/61033` |
| Positions | `/positions/72044` |
| Listings | `/listings/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
