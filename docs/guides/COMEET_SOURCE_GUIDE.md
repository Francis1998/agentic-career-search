# Comeet Source Guide

![Comeet discovery flow](../../assets/demo/comeet-source.gif)

Use this guide when wiring a public Comeet careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Comeet

Comeet (`www.comeet.co` / `www.comeet.com`) is a widely used ATS for growth and
enterprise hiring teams. Public boards expose each job as an anchor under
`/jobs/{company}/{companyId}/{jobSlug}/{jobId}`. This adapter mirrors the
Freshteam/Teamtailor/Pinpoint URL-shape approach used for other HTML careers
sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-comeet",
    "source_type": "comeet",
    "base_url": "https://www.comeet.co/careers/acme-corp"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Job detail (`.co`) | `/jobs/acme-corp/5a1b2c3d/senior-engineer/550e8400-e29b-41d4-a716-446655440000` |
| Job detail (`.com`) | `https://www.comeet.com/jobs/acme-corp/5a1b2c3d/platform-engineer/7dcb7727-4fe1-47d6-bb17-82636428b228` |

Board index pages (`/jobs/{company}/{companyId}`), apply/login steps
(`/jobs/.../{jobId}/apply`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Terminal `{jobId}` segment |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Comeet APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-098 for the design decision.
