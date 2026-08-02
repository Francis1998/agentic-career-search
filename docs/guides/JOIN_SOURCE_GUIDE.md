# Join Source Guide

![Join discovery flow](../../assets/demo/join-source.gif)

Use this guide when wiring a public Join careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Join

Join (`join.com`) is an ATS popular with European startups and scale-ups. Public
boards expose each job as an anchor under `/companies/{slug}/jobs/{id}`,
`/jobs/{id}`, `/job/{id}`, or `/positions/{id}` detail paths. This adapter
mirrors the Recruiterflow/ClearCompany URL-shape approach used for other HTML
careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-join",
    "source_type": "join",
    "base_url": "https://join.com/companies/acme-corp"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Company jobs | `/companies/acme-corp/jobs/48291` |
| Jobs | `/jobs/55902` |
| Job | `/job/61033` |
| Positions | `/positions/72044` |

Board index pages (`/jobs`, `/companies/{slug}/jobs`, `/positions`), apply/login
steps (`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Bare id from recognised detail path |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Join APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-112 for the design decision.
