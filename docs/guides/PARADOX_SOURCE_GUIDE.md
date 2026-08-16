# Paradox Source Guide

![Paradox discovery flow](../../assets/demo/paradox-source.gif)

Use this guide when wiring a public Paradox Olivia careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching -
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Paradox

Paradox (`*.paradox.ai`) is a conversational recruiting platform whose Olivia
assistant powers public careers pages. Boards commonly expose each job as an
anchor under `/jobs/{id}`, `/job/{id}`, `/careers/{id}`,
`/careers/job/{id}`, or `/opportunities/{id}` detail paths.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-paradox",
    "source_type": "paradox",
    "base_url": "https://acme.paradox.ai/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Careers | `/careers/61033` |
| Careers job | `/careers/job/72044` |
| Opportunities | `/opportunities/83055` |

Board index pages (`/jobs`, `/careers`, `/opportunities`), apply/login steps,
and navigation links are ignored.

## Safety

- Public careers pages only - no authenticated Paradox APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-142 for the design decision.
