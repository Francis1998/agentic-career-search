# Fountain Source Guide

![Fountain discovery flow](../../assets/demo/fountain-source.gif)

Use this guide when wiring a public Fountain careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Fountain

Fountain (`{org}.fountain.com` / `web.fountain.com`) is a widely used hiring
platform for hourly and frontline teams. Public boards expose each job as an
anchor under `/apply/{company}/{positionId}`, tenant `/apply/{slug}`, or
`/jobs/{jobId}` / `/openings/{id}` / `/positions/{id}` paths. This adapter
mirrors the Freshteam/Teamtailor/Pinpoint URL-shape approach used for other
HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-fountain",
    "source_type": "fountain",
    "base_url": "https://acme.fountain.com/"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Tenant apply slug | `/apply/senior-engineer-abc123` |
| Web apply detail | `https://web.fountain.com/apply/acme-corp/platform-eng-def456` |
| Jobs path | `/jobs/job789` |
| Openings path | `/openings/open001` |
| Positions path | `/positions/pos999` |

Board index pages (`/apply`, `/apply/{company}` on `web.fountain.com`),
apply confirmation/login steps, and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Terminal position/job id segment |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Fountain APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-099 for the design decision.
