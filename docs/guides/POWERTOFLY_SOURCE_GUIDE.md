# PowerToFly Source Guide

![PowerToFly discovery flow](../../assets/demo/powertofly-source.gif)

Use this guide when wiring a public PowerToFly careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why PowerToFly

PowerToFly is a diversity-focused remote board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "powertofly-jobs",
    "source_type": "powertofly",
    "base_url": "https://powertofly.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Opportunities | `/opportunities/50113` |
| Women Tech | `/women-tech/57224` |
| Positions | `/positions/63335` |
| Jobs | `/jobs/74446` |
| Job | `/job/85557` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
