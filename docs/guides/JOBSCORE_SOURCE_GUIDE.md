# JobScore Source Guide

![JobScore discovery flow](../../assets/demo/jobscore-source.gif)

Use this guide when wiring a public JobScore careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why JobScore

JobScore (`careers.jobscore.com` / `*.jobscore.com`) is a widely used ATS for
mid-market and growth hiring teams. Public boards expose each job as an anchor
under `/careers/{company}/jobs/...`, or under `/jobs/...` and `/position(s)/...`
detail paths. This adapter mirrors the Gem/Fountain/Teamtailor URL-shape
approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-jobscore",
    "source_type": "jobscore",
    "base_url": "https://careers.jobscore.com/careers/acme"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Careers + slug-id | `/careers/acme/jobs/software-engineer-48291` |
| Careers + bare id | `/careers/acme/jobs/55902` |
| Jobs prefix | `/jobs/61033` |
| Jobs + slug/id | `/jobs/data-engineer/72144` |
| Position | `/position/83355` |
| Positions | `/positions/94466` |

Board index pages (`/careers/acme`, `/careers/acme/jobs`), apply/login steps
(`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Trailing `{id}` token (from `{slug}-{id}`, `/jobs/{slug}/{id}`, or bare id) |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated JobScore APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-101 for the design decision.
