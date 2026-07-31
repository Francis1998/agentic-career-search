# Hireology Source Guide

![Hireology discovery flow](../../assets/demo/hireology-source.gif)

Use this guide when wiring a public Hireology careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Hireology

Hireology (`careers.hireology.com`) is a widely used ATS for franchise, retail,
and multi-location hiring teams. Public boards expose each job as an anchor
under `/jobs/{id}`, `/careers/job/{id}`, or `/job/{id}/{slug}` detail paths.
This adapter mirrors the JobScore/Avature URL-shape approach used for other HTML
careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-hireology",
    "source_type": "hireology",
    "base_url": "https://careers.hireology.com/acme"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Jobs prefix | `/jobs/48291` |
| Careers job | `/careers/job/55902` |
| Job + slug | `/job/61033/software-engineer` |

Board index pages (`/careers`, `/jobs`, `/careers/job`), apply/login steps
(`/{id}/apply`, `/login`, `/signin`), and navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Trailing `{id}` token from recognised detail paths |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Hireology APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-104 for the design decision.
