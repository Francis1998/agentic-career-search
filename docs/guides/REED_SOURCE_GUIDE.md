# Reed Source Guide

![Reed discovery flow](../../assets/demo/reed-source.gif)

Use this guide when wiring a public Reed careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Reed

Reed is a leading UK job board often present in European aggregators but missing here; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "reed-jobs",
    "source_type": "reed",
    "base_url": "https://www.reed.co.uk/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/{id}` |
| Job | `/job/{id}` |
| Details | `/details/{id}` |
| Vacancies | `/vacancies/{id}` |
| Listings | `/listings/{id}` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
