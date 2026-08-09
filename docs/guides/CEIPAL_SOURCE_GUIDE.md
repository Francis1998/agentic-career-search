# Ceipal Source Guide

![Ceipal discovery flow](../../assets/demo/ceipal-source.gif)

Use this guide when wiring a public Ceipal careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching -
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Ceipal

Ceipal (`jobs.ceipal.com`) is an ATS used by employers that publish public
careers pages. Boards commonly expose each job as an anchor under `/jobs/{id}`,
`/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, or
`/requisitions/{id}` detail paths. This adapter mirrors the Jobylon URL-shape
approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-ceipal",
    "source_type": "ceipal",
    "base_url": "https://jobs.ceipal.com/acme/jobs/"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Careers | `/careers/61033` |
| Careers job | `/careers/job/72044` |
| Requisitions | `/requisitions/83055` |

Board index pages (`/jobs`, `/careers`, `/requisitions`),
apply/login steps (`/{id}/apply`, `/login`, `/signin`), and navigation links are
ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Bare id from recognised detail path |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only - no authenticated Ceipal APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-124 for the design decision.

## Suggested repo metadata

- **Description:** Agentic job-search automation with multi-ATS adapters, decision engine, and GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 enrichment.
- **Topics:** `agentic-ai`, `job-search`, `ats`, `career-automation`, `llm`, `python`, `fastapi`
