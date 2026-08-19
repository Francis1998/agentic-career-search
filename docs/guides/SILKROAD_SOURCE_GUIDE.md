# SilkRoad Recruiting Source Guide

![SilkRoad Recruiting discovery flow](../../assets/demo/silkroad-source.gif)

Use this guide when wiring a public SilkRoad Recruiting careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching -
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why SilkRoad Recruiting

SilkRoad Recruiting (`*.silkroad.com`) provides recruiting boards used by
employers to publish public careers pages. Boards commonly expose each job as
an anchor under the detail paths below. Popular ATS ecosystems (Greenhouse,
Lever, Workday) already ship first-party adapters here; SilkRoad / Radancy /
Jibe close remaining enterprise board gaps for employer-brand career sites.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-silkroad",
    "source_type": "silkroad",
    "base_url": "https://acme.example.com/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Posting | `/posting/61033` |
| Postings | `/postings/72044` |
| Opportunity | `/opportunity/83055` |

Board index pages, apply/login steps, and navigation links are ignored.

## Safety

- Public HTML only — no authenticated SilkRoad Recruiting APIs.
- Deterministic URL-shape matching (ADR-077); optional LLM enrichment is
  separate and must not invent postings.
