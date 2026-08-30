# No Fluff Jobs Source Guide

![No Fluff Jobs discovery flow](../../assets/demo/nofluffjobs-source.gif)

Use this guide when wiring a public No Fluff Jobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why No Fluff Jobs

No Fluff Jobs is a popular EU tech board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "nofluffjobs-jobs",
    "source_type": "nofluffjobs",
    "base_url": "https://nofluffjobs.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| PL | `/pl/70113` |
| Job | `/job/77224` |
| Offers | `/offers/83335` |
| Positions | `/positions/94446` |
| Jobs | `/jobs/105557` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
