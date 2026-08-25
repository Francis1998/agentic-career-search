# Jobspresso Source Guide

![Jobspresso discovery flow](../../assets/demo/jobspresso-source.gif)

Use this guide when wiring a public Jobspresso careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Jobspresso

Jobspresso publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /remote-jobs/{id}, /postings/{id}, /openings/{id}. Remote marketplace scrapers commonly include Jobspresso; this repo's board adapters left Jobspresso without deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "jobspresso-jobs",
    "source_type": "jobspresso",
    "base_url": "https://jobspresso.co/remote-jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Remote Jobs | `/remote-jobs/61033` |
| Postings | `/postings/72044` |
| Openings | `/openings/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
