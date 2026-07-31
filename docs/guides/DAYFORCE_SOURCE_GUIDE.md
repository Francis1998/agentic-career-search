# Dayforce Source Guide

![Dayforce discovery flow](../../assets/demo/dayforce-source.gif)

Use this guide when wiring a public Dayforce (Ceridian) careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Dayforce

Dayforce (`*.dayforcehcm.com` / tenant vanity domains) is an enterprise HCM
platform whose public boards expose each job as an anchor under `/JobDetail/...`,
`/careers/job/...`, `/MyCareer/JobDetail?jobId=...`, or `/positions/...` detail
paths. This adapter mirrors the Avature/JobScore URL-shape approach used for
other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-dayforce",
    "source_type": "dayforce",
    "base_url": "https://careers.dayforcehcm.com/acme"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| JobDetail | `/JobDetail/184291` |
| Careers job | `/careers/job/90210` |
| MyCareer query | `/MyCareer/JobDetail?jobId=44102` |
| Positions | `/positions/33110` |
| Position | `/position/33110` |

Board index pages (`/careers`, `/positions`, `/JobDetail`), apply/login steps
(`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Path-segment `{id}` or `jobId` query parameter |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Dayforce APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-105 for the design decision.
