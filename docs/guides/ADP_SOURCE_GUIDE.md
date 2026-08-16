# ADP Recruiting Source Guide

![ADP Recruiting discovery flow](../../assets/demo/adp-source.gif)

Use this guide when wiring a public ADP Recruiting careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching -
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why ADP Recruiting

ADP (`*.adp.com`) provides recruiting boards used by employers to publish
public careers pages. Boards commonly expose each job as an anchor under
`/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, or
`/requisitions/{id}` detail paths.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-adp",
    "source_type": "adp",
    "base_url": "https://acme.adp.com/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Careers | `/careers/61033` |
| Careers job | `/careers/job/72044` |
| Requisitions | `/requisitions/83055` |

Board index pages (`/jobs`, `/careers`, `/requisitions`), apply/login steps,
and navigation links are ignored.

## Safety

- Public careers pages only - no authenticated ADP APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-143 for the design decision.
