# Arc.dev Source Guide

![Arc.dev discovery flow](../../assets/demo/arcdev-source.gif)

Use this guide when wiring a public Arc.dev careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Arc.dev

Arc.dev (formerly CodementorX) is a remote tech hiring board gap; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "arcdev-jobs",
    "source_type": "arcdev",
    "base_url": "https://arc.dev/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Roles | `/roles/61033` |
| Positions | `/positions/72044` |
| Openings | `/openings/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
