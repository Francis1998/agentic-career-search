# Wellfound Source Guide

![Wellfound discovery flow](../../assets/demo/wellfound-source.gif)

Use this guide when wiring a public Wellfound careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Wellfound

Wellfound (formerly AngelList Talent) is a startup hiring platform whose public career pages commonly link to detail pages under /jobs/{id}, /job/{id}, /role/{id}, /roles/{id}, or /startup-jobs/{id}. JobSpy and Greenhouse-style API clients cover common ATS boards, but leave gaps for Wellfound/AngelList public startup job pages.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-wellfound",
    "source_type": "wellfound",
    "base_url": "https://wellfound.com/company/acme/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Role | `/role/61033` |
| Roles | `/roles/72044` |
| Startup Jobs | `/startup-jobs/83055` |

Board index pages, apply/login steps, and navigation links are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
