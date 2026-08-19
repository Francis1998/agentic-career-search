# Jibe Source Guide

![Jibe discovery flow](../../assets/demo/jibe-source.gif)

Use this guide when wiring a public Jibe careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching -
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Jibe

Jibe (`*.jibe.com / *.jibestream.com`) provides recruiting boards used by
employers to publish public careers pages. Boards commonly expose each job as
an anchor under the detail paths below. Popular ATS ecosystems (Greenhouse,
Lever, Workday) already ship first-party adapters here; SilkRoad / Radancy /
Jibe close remaining enterprise board gaps for employer-brand career sites.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-jibe",
    "source_type": "jibe",
    "base_url": "https://acme.example.com/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Position | `/position/61033` |
| Positions | `/positions/72044` |
| Requisition | `/requisition/83055` |

Board index pages, apply/login steps, and navigation links are ignored.

## Safety

- Public HTML only — no authenticated Jibe APIs.
- Deterministic URL-shape matching (ADR-077); optional LLM enrichment is
  separate and must not invent postings.
