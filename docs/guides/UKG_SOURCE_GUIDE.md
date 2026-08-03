# UKG Source Guide

![UKG discovery flow](../../assets/demo/ukg-source.gif)

Use this guide when wiring a public UKG careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why UKG

UKG (`*.ultipro.com / *.ukg.net`) is a major ATS/HR platform. Public boards
expose each job as an anchor under recognised detail paths. This adapter mirrors
the Softgarden/Factorial URL-shape approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-ukg",
    "source_type": "ukg",
    "base_url": "https://acme.ultipro.com"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/48291` |
| Opportunities | `/opportunities/48291` |
| Opportunity | `/opportunity/48291` |
| Careers/Job | `/careers/job/48291` |

Board index pages, apply/login steps (`/{id}/apply`, `/login`, `/signin`), and
navigation links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Bare id from recognised detail path |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated UKG APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-114 for the design decision.

## Suggested repo metadata

- **Description:** Agentic job-search automation with multi-ATS adapters, decision engine, and GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 enrichment.
- **Topics:** `agentic-ai`, `job-search`, `ats`, `career-automation`, `llm`, `python`, `fastapi`
