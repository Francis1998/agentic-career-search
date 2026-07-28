# Phenom People Source Guide

![Phenom discovery flow](../../assets/demo/phenom-source.gif)

Use this guide when wiring a public Phenom People careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5, Claude Sonnet 4.6, Gemini 3.x, or Kimi K2 is optional
and runs after candidates are collected.

## Why Phenom People

Phenom People is common on enterprise careers sites and branded talent
experiences. Public boards often expose posting detail anchors under
`/job/{id}/{slug}` or `/jobs/{id}` paths while rendering list, login, and apply
links in the same page. The adapter follows the JazzHR/Breezy HR pattern: parse
all anchors, keep only stable posting detail shapes, and normalize them into
`JobCandidate` records.

## Register a source

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-phenom",
    "source_type": "phenom",
    "base_url": "https://careers.example.com/us/en/search-results"
  }'
```

Any public listing URL for the tenant works. The adapter extracts postings from:

| Shape | Example |
|---|---|
| Path `/job/{id}/{slug}` | `/job/PHENOM-1234/platform-engineer` |
| Locale-prefixed `/job/{id}/{slug}` | `/us/en/job/R_7788/site-reliability-engineer` |
| Path `/jobs/{id}` | `/jobs/987654` |

List/index/search pages, login links, and application-step links are ignored.

## What you get

| Field | Source |
|---|---|
| `title` | Anchor text, else `title` attribute |
| `location` | Nearest posting-container location text |
| `external_id` | Phenom `/job` or `/jobs` path id |
| `url` | Absolute posting URL |
| `company` | Host-derived token |

## Safety notes

- Public careers pages only — no authenticated Phenom APIs.
- Outbound User-Agent comes from settings.
- Parsing stops at `max_jobs`; no unbounded crawl.

See ADR-095 for the design decision.
