# JazzHR Source Guide

![JazzHR discovery flow](../../assets/demo/jazzhr-source.gif)

Use this guide when wiring a public JazzHR careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching —
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why JazzHR

JazzHR is common across small and mid-market career sites and is often published
from `{tenant}.applytojob.com/apply`. Unlike Greenhouse boards, postings are
linked by JazzHR apply paths rather than a single CSS class. This adapter mirrors
the SuccessFactors/Taleo/Zoho Recruit approach used by ATS URL-shape scrapers.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-jazzhr",
    "source_type": "jazzhr",
    "base_url": "https://acme.applytojob.com/apply"
  }'
```

Any public listing URL works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Path `/apply/{id}` | `/apply/JAZZ-1234` |
| Path `/apply/{id}/{slug}` | `/apply/JAZZ_7788/site-reliability-engineer` |

Apply-root links, search pages, legacy `/jobs/...` links, and deeper application
steps are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` attribute |
| `location` | Nearest posting-container location text |
| `external_id` | JazzHR `/apply/{id}` path segment |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated JazzHR APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-093 for the design decision.
