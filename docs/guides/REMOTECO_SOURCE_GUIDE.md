# Remote.co Source Guide

![Remote.co discovery flow](../../assets/demo/remoteco-source.gif)

Use this guide when wiring a public Remote.co careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Remote.co

Remote.co is a popular remote job board gap versus Remotive/WeWorkRemotely/Himalayas already in this repo; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "remoteco-jobs",
    "source_type": "remoteco",
    "base_url": "https://remote.co/remote-jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Remote Jobs | `/remote-jobs/61033` |
| Jobs | `/jobs/48291` |
| Job | `/job/55902` |
| Positions | `/positions/72044` |
| Careers | `/careers/83055` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
