# Pinpoint Source Guide

![Pinpoint discovery flow](../../assets/demo/pinpoint-source.gif)

Use this guide when wiring a public Pinpoint HR careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Pinpoint

Pinpoint (`{org}.pinpointhq.com`) is a widely used ATS for mid-market hiring
teams. Public boards expose each job as an anchor under `/postings/{uuid}`
(optionally locale-prefixed) or `/jobs/{jobId}`. This adapter mirrors the
Freshteam/Teamtailor/BreezyHR URL-shape approach used for other HTML careers
sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-pinpoint",
    "source_type": "pinpoint",
    "base_url": "https://acme.pinpointhq.com/"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Posting UUID | `/postings/baa10d0a-1485-472b-a813-89a6688e4e97` |
| Locale + posting UUID | `/en/postings/baa10d0a-1485-472b-a813-89a6688e4e97` |
| Job id + slug | `/jobs/53913/customer-success-manager` |
| Job id only | `/jobs/53913` |

Apply/login steps (`/postings/{uuid}/apply`, `/jobs/{id}/application`) and
board navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | `/postings/{uuid}` or `/jobs/{jobId}` token |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Pinpoint APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-097 for the design decision.
