# Recruiterflow Source Guide

![Recruiterflow discovery flow](../../assets/demo/recruiterflow-source.gif)

Use this guide when wiring a public Recruiterflow careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Recruiterflow

Recruiterflow (`*.recruiterflow.com`) is an ATS for recruiting agencies and
growing companies. Public boards expose each job as an anchor under `/jobs/{id}`,
`/job/{id}`, `/careers/job/{id}`, `/openings/{id}`, or `/opening/{id}` detail
paths. This adapter mirrors the Homerun/Hireology URL-shape approach used for
other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-recruiterflow",
    "source_type": "recruiterflow",
    "base_url": "https://acme.recruiterflow.com"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Careers job | `/careers/job/61033` |
| Openings | `/openings/72044` |
| Opening | `/opening/83055` |

Board index pages (`/jobs`, `/openings`, `/opening`), apply/login steps
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

- Public careers pages only — no authenticated Recruiterflow APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-109 for the design decision.
