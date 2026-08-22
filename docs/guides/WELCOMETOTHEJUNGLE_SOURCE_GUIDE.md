# Welcome to the Jungle Source Guide

![Welcome to the Jungle discovery flow](../../assets/demo/welcometothejungle-source.gif)

Use this guide when wiring a public Welcome to the Jungle careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Welcome to the Jungle

Welcome to the Jungle publishes career boards whose public listings commonly
link to detail pages under /jobs/{id}, /job/{id}, /companies/{slug}/jobs/{id},
/offers/{id}, or /offer/{id}. ATS-focused adapters leave WTTJ marketplace
boards without deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "wttj-jobs",
    "source_type": "welcometothejungle",
    "base_url": "https://www.welcometothejungle.com/en/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Company Jobs | `/companies/acme/jobs/61033` |
| Offers | `/offers/72044` |
| Offer | `/offer/83055` |

Board index pages, bare company pages, apply/login steps, about/index links,
and navigation links are ignored. For company job URLs the job id segment is
used as `external_id`.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
