# ClearCompany Source Guide

![ClearCompany discovery flow](../../assets/demo/clearcompany-source.gif)

Use this guide when wiring a public ClearCompany careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why ClearCompany

ClearCompany (`*.clearcompany.com`) is a widely used ATS for mid-market employers
and staffing firms. Public boards expose each job as an anchor under
`/careers/job/{id}`, `/careers/{id}`, `/jobs/{id}`, `/job/{id}-{slug}`, or
`/position/{id}` detail paths. This adapter mirrors the Homerun/Hireology
URL-shape approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-clearcompany",
    "source_type": "clearcompany",
    "base_url": "https://acme.clearcompany.com"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Careers job | `/careers/job/48291` |
| Careers id | `/careers/55902` |
| Jobs | `/jobs/61033` |
| Job slug-id | `/job/72044-software-engineer` |
| Position | `/position/83055` |

Board index pages (`/jobs`, `/careers`, `/position`), apply/login steps
(`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Leading `{id}` token from `{id}-{slug}` or bare id from other shapes |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated ClearCompany APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-107 for the design decision.
