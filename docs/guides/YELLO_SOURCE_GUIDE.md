# Yello Source Guide

![Yello discovery flow](../../assets/demo/yello-source.gif)

Use this guide when wiring a public Yello careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Yello

Yello provides recruiting and early-talent experiences used by employers to
publish public careers pages. Boards commonly expose each job as an anchor
under the detail paths below. The adapter fills public HTML discovery gaps
left by broad tools such as JobSpy and Greenhouse-style board clients.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-yello",
    "source_type": "yello",
    "base_url": "https://acme.yello.co/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Position | `/position/61033` |
| Positions | `/positions/72044` |
| Opening | `/opening/83055` |

Board index pages, apply/login steps, and navigation links are ignored.

## Safety

- Public HTML only — no authenticated Yello APIs.
- Deterministic URL-shape matching (ADR-077); optional LLM enrichment is
  separate and must not invent postings.
