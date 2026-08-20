# Paycom Source Guide

![Paycom discovery flow](../../assets/demo/paycom-source.gif)

Use this guide when wiring a public Paycom careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Paycom

Paycom provides HR and recruiting experiences used by employers to publish
public careers pages. Boards commonly expose each job as an anchor under the
detail paths below. The adapter fills public HTML discovery gaps left by broad
tools such as JobSpy and Greenhouse-style board clients.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "acme-paycom",
    "source_type": "paycom",
    "base_url": "https://acme.paycomonline.net/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Posting | `/posting/61033` |
| Postings | `/postings/72044` |
| Opportunity | `/opportunity/83055` |

Board index pages, apply/login steps, and navigation links are ignored.

## Safety

- Public HTML only — no authenticated Paycom APIs.
- Deterministic URL-shape matching (ADR-077); optional LLM enrichment is
  separate and must not invent postings.
