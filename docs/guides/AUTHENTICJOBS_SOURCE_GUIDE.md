# Authentic Jobs Source Guide

![Authentic Jobs discovery flow](../../assets/demo/authenticjobs-source.gif)

Use this guide when wiring a public Authentic Jobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Authentic Jobs

Authentic Jobs is a design/creative hiring board gap relative to jobSpy/RemoteOK scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "authenticjobs-jobs",
    "source_type": "authenticjobs",
    "base_url": "https://authenticjobs.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Postings | `/postings/48291` |
| Listing | `/listing/55902` |
| Opportunities | `/opportunities/61033` |
| Jobs | `/jobs/72044` |
| Job | `/job/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
