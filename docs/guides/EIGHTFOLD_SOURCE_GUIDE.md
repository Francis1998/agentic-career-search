# Eightfold Source Guide

![Eightfold discovery flow](../../assets/demo/eightfold-source.gif)

Use this guide when wiring a public Eightfold AI careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Eightfold

Eightfold (`{company}.eightfold.ai`) is a widely used talent-intelligence ATS
for enterprise hiring teams. Public boards expose each job as an anchor under
`/careers/job/{id}` (optional slug), `/career_detail/{id}`, `/position/{id}`, or
`/jobs/{id}`. This adapter mirrors the Gem/Freshteam/Teamtailor/Pinpoint
URL-shape approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-eightfold",
    "source_type": "eightfold",
    "base_url": "https://acme.eightfold.ai/careers"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Careers job id | `/careers/job/24123` |
| Careers job id + slug | `/careers/job/PID-88901/platform-engineer` |
| Career detail | `/career_detail/EF-48291` |
| Position prefix | `/position/POS-1001` |
| Jobs prefix | `/jobs/7788` |

Board index pages (`/careers`), apply/login steps (`/{id}/apply`), search
facets, and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Terminal `{id}` token |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Eightfold Talent Acquisition APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-102 for the design decision.
