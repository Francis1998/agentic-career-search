# Himalayas Source Guide

![Himalayas discovery flow](../../assets/demo/himalayas-source.gif)

Use this guide when wiring a public Himalayas careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Himalayas

Himalayas publishes remote job boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /companies/{slug}/jobs/{id},
/remote-jobs/{id}, or /roles/{id}. ATS-focused adapters leave Himalayas
aggregator boards without deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "himalayas-remote",
    "source_type": "himalayas",
    "base_url": "https://himalayas.app/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Company Jobs | `/companies/acme/jobs/61033` |
| Remote Jobs | `/remote-jobs/72044` |
| Roles | `/roles/83055` |

Board index pages, bare company pages, apply/login steps, about/index links,
and navigation links are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
