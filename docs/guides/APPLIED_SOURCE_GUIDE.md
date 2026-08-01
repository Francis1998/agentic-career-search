# Applied Source Guide

![Applied discovery flow](../../assets/demo/applied-source.gif)

Use this guide when wiring a public Applied careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Applied

Applied (`*.applied.co`) is a modern ATS for startups and scale-ups. Public
boards expose each job as an anchor under `/jobs/{id}`, `/j/{id}`,
`/role/{id}`, `/roles/{id}`, or `/job/{id}` detail paths. Applied.co boards
often use `/jobs/{uuid-or-slug}` identifiers. This adapter mirrors the
Homerun/Hireology URL-shape approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-applied",
    "source_type": "applied",
    "base_url": "https://acme.applied.co"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Jobs uuid/slug | `/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| Short | `/j/55902` |
| Role | `/role/61033` |
| Roles | `/roles/72044` |
| Job | `/job/83055` |

Board index pages (`/jobs`, `/roles`, `/j`), apply/login steps
(`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Path segment id (uuid, slug, or numeric) |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Applied APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-108 for the design decision.
