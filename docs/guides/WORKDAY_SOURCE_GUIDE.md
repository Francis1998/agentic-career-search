# Workday Source Guide

![Workday CXS discovery flow](../../assets/demo/agentic-career-search-demo.gif)

Use this guide when wiring a public Workday careers board into
**agentic-career-search**. The agent routes discovery through GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 enrichment when enabled, but the
Workday adapter itself is deterministic JSON — no LLM required to list openings.

## Why Workday

Popular job-search stacks (jobo.world ATS scrapers, career-ops, Greenhouse/Lever
kits) all treat Workday as the hard case: the careers page is a client-rendered
SPA, so HTML scrapers return nothing. Workday exposes the same public CXS API
the SPA uses:

```
POST /wday/cxs/{tenant}/{site}/jobs
{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
```

Hard page size is **20**. Larger limits return an empty `jobPostings` array.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "nvidia-workday",
    "source_type": "workday",
    "base_url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
  }'
```

Any careers URL for the tenant/site works — with or without the `en-US` locale
segment. The adapter derives `tenant`, `site`, and the CXS endpoint automatically.

## What you get

| Field | Source |
|---|---|
| `title` | CXS `title` |
| `location` | CXS `locationsText` |
| `external_id` | Trailing `JR…` / `R-…` after `_` in `externalPath` |
| `url` | `{origin}/{locale}/{site}{externalPath}` |
| `company` | Host-derived token |

## Safety notes

- Public CXS only — no authenticated Workday tenant APIs.
- Outbound User-Agent comes from settings; Referer mirrors the careers origin.
- Pagination stops at `max_jobs` or a short page; no unbounded crawl.

See ADR-088 for the design decision.
