# CATS Source Guide

![CATS discovery flow](../../assets/demo/catsone-source.gif)

Use this guide when wiring a public CATS careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching -
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why CATS

CATS (`*.catsone.com`) is an ATS used by employers and recruiting agencies that
publish public careers pages. Boards commonly expose each job as an anchor
under `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, or
`/postings/{id}` detail paths.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-cats",
    "source_type": "catsone",
    "base_url": "https://acme.catsone.com/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Careers | `/careers/61033` |
| Careers job | `/careers/job/72044` |
| Postings | `/postings/83055` |

Board index pages (`/jobs`, `/careers`, `/postings`), apply/login steps, and
navigation links are ignored.

## Safety

- Public careers pages only - no authenticated CATS APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-141 for the design decision.
