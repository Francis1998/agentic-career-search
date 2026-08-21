# Otta Source Guide

![Otta discovery flow](../../assets/demo/otta-source.gif)

Use this guide when wiring a public Otta careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Otta

Otta is a UK/EU tech careers marketplace whose public listing pages commonly link to detail pages under /jobs/{id}, /job/{id}, /roles/{id}, /role/{id}, or /openings/{id}. Popular scrapers such as JobSpy emphasize aggregator boards and leave Otta employer/marketplace detail pages undercovered.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-otta",
    "source_type": "otta",
    "base_url": "https://app.otta.com/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Roles | `/roles/61033` |
| Role | `/role/72044` |
| Openings | `/openings/83055` |

Board index pages, apply/login steps, and navigation links are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
