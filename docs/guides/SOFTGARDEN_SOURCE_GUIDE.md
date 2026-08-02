# Softgarden Source Guide

![Softgarden discovery flow](../../assets/demo/softgarden-source.gif)

Use this guide when wiring a public Softgarden careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Softgarden

Softgarden (`*.softgarden.io`) is an ATS popular with European employers.
Public boards expose each job as an anchor under `/job/{id}`, `/jobs/{id}`,
`/vacancies/{id}`, `/vacancy/{id}`, or `/position/{id}` detail paths. This
adapter mirrors the ClearCompany/Recruiterflow URL-shape approach used for
other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-softgarden",
    "source_type": "softgarden",
    "base_url": "https://acme.softgarden.io"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Job | `/job/48291` |
| Jobs | `/jobs/55902` |
| Vacancies | `/vacancies/61033` |
| Vacancy | `/vacancy/72044` |
| Position | `/position/83055` |

Board index pages (`/jobs`, `/vacancies`, `/position`), apply/login steps
(`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Bare id from recognised detail path |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Softgarden APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-111 for the design decision.
