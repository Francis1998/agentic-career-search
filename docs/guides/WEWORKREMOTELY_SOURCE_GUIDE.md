# WeWorkRemotely Source Guide

![WeWorkRemotely discovery flow](../../assets/demo/weworkremotely-source.gif)

Use this guide when wiring a public WeWorkRemotely careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why WeWorkRemotely

WeWorkRemotely publishes remote job boards whose public listings commonly link
to detail pages under /remote-jobs/{id}, /jobs/{id}, /job/{id}, /listings/{id},
or /listing/{id}. ATS-focused adapters leave WeWorkRemotely aggregator boards
without deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "wwr-remote",
    "source_type": "weworkremotely",
    "base_url": "https://weworkremotely.com/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Remote Jobs | `/remote-jobs/48291` |
| Jobs | `/jobs/55902` |
| Job | `/job/61033` |
| Listings | `/listings/72044` |
| Listing | `/listing/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
