# FlexJobs Source Guide

![FlexJobs discovery flow](../../assets/demo/flexjobs-source.gif)

Use this guide when wiring a public FlexJobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why FlexJobs

FlexJobs is a popular curated remote-job board gap relative to jobSpy/RemoteOK scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "flexjobs-jobs",
    "source_type": "flexjobs",
    "base_url": "https://www.flexjobs.com/search"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Search | `/search/48291` |
| Flex jobs | `/flex-jobs/55902` |
| Remote job | `/remote-job/61033` |
| Jobs | `/jobs/72044` |
| Job | `/job/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
