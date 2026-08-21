# Built In Source Guide

![Built In discovery flow](../../assets/demo/builtin-source.gif)

Use this guide when wiring a public Built In careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Built In

Built In publishes city and national tech career boards whose public listings commonly link to detail pages under /job/{id}, /jobs/{id}, /company-jobs/{id}, /careers/job/{id}, or /role/{id}. ATS-focused adapters leave Built In city boards (similar to RemoteOK/WWR aggregator gaps) without deterministic HTML discovery.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-builtin",
    "source_type": "builtin",
    "base_url": "https://builtin.com/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Job | `/job/48291` |
| Jobs | `/jobs/55902` |
| Company Jobs | `/company-jobs/61033` |
| Careers Job | `/careers/job/72044` |
| Role | `/role/83055` |

Board index pages, apply/login steps, and navigation links are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
