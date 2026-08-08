# Loxo Source Guide

![Loxo discovery flow](../../assets/demo/loxo-source.gif)

Use this guide when wiring a public Loxo careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Loxo

Loxo (`*.loxo.co`) is an ATS popular with recruiting agencies and growth-stage
companies. Public boards expose each job as an anchor under `/jobs/{id}`,
`/job/{id}`, `/positions/{id}`, `/careers/{id}`, or `/careers/job/{id}` detail
paths. This adapter mirrors the Softgarden/Manatal URL-shape approach used for
other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-loxo",
    "source_type": "loxo",
    "base_url": "https://acme.loxo.co"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Positions | `/positions/61033` |
| Careers | `/careers/72044` |
| Careers job | `/careers/job/83055` |

Board index pages (`/jobs`, `/careers`, `/positions`), apply/login steps
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

- Public careers pages only — no authenticated Loxo APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-117 for the design decision.

## Suggested repo metadata

- **Description:** Agentic job-search automation with multi-ATS adapters, decision engine, and GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 enrichment.
- **Topics:** `agentic-ai`, `job-search`, `ats`, `career-automation`, `llm`, `python`, `fastapi`
