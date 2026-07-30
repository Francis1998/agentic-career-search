# Avature Source Guide

![Avature discovery flow](../../assets/demo/avature-source.gif)

Use this guide when wiring a public Avature careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Avature

Avature hosts enterprise recruiting CRM/ATS career portals. Public boards
expose each job as an anchor under `/JobDetail/{id}`, the legacy
`/JobDetail.aspx?JobId={id}` query form, `/careers/...` vanity paths, or
`/Vacancy/{id}` / `/vacancies/{id}`. This adapter mirrors the
Gem/Fountain/Freshteam URL-shape approach used for other HTML careers sources.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-avature",
    "source_type": "avature",
    "base_url": "https://careers.acme.com/careers"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| JobDetail path | `/JobDetail/184291` |
| JobDetail.aspx query | `/JobDetail.aspx?JobId=90210` |
| Careers id | `/careers/vac-44102` |
| Careers job | `/careers/job/184291` |
| Careers VacancyDetail | `/careers/VacancyDetail/33110` |
| Vacancy path | `/Vacancy/33110` |
| Vacancies path | `/vacancies/90210` |

Board index pages (`/careers`, `/vacancies`, `/JobDetail`), apply/login steps,
`RegisterCandidate`, and navigation links are ignored. When both a path id and
a `JobId` query value are present, the path-segment id is preferred.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` / `aria-label` / `data-job-title` |
| `location` | `data-location` / `data-job-location`, remote flag, or nearest posting-container location text |
| `external_id` | Path `{id}` token, else `JobId` query value |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Avature APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-103 for the design decision.
