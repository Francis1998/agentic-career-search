# EuroTechJobs Source Guide

![EuroTechJobs discovery flow](../../assets/demo/eurotechjobs-source.gif)

Use this guide when wiring a public EuroTechJobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why EuroTechJobs

EuroTechJobs covers Europe-focused tech hiring board gap relative to jobSpy/RemoteOK scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "eurotechjobs-jobs",
    "source_type": "eurotechjobs",
    "base_url": "https://www.eurotechjobs.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Vacancies | `/vacancies/48291` |
| Offers | `/offers/55902` |
| Tech jobs | `/tech-jobs/61033` |
| Jobs | `/jobs/72044` |
| Job | `/job/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
