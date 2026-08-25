# JustRemote Source Guide

![JustRemote discovery flow](../../assets/demo/justremote-source.gif)

Use this guide when wiring a public JustRemote careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why JustRemote

JustRemote publishes career boards whose public listings commonly link to
detail pages under /remote-jobs/{id}, /jobs/{id}, /job/{id}, /listings/{id}, /listing/{id}. JobSpy-style remote aggregators cover JustRemote boards, but this repo's ATS-focused adapters left JustRemote marketplace boards without deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "justremote-jobs",
    "source_type": "justremote",
    "base_url": "https://justremote.co/remote-jobs"
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
