# Homerun Source Guide

![Homerun discovery flow](../../assets/demo/homerun-source.gif)

Use this guide when wiring a public Homerun careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Homerun

Homerun (`{company}.homerun.co`) is a widely used ATS for European startups and
scale-ups. Public boards expose each job as an anchor under `/jobs/{id}-{slug}`,
`/o/{id}`, or `/vacancies/{id}` detail paths. This adapter mirrors the
Teamtailor/JobScore URL-shape approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-homerun",
    "source_type": "homerun",
    "base_url": "https://acme.homerun.co"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Jobs slug-id | `/jobs/48291-software-engineer` |
| Short opening | `/o/55902` |
| Vacancies | `/vacancies/61033` |
| Vacancy | `/vacancy/48291` |

Board index pages (`/jobs`, `/vacancies`, `/o`), apply/login steps
(`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Leading `{id}` token from `{id}-{slug}` or bare id from `/o/{id}` / `/vacancies/{id}` |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Homerun APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-106 for the design decision.
