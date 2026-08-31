# Dice Source Guide

![Dice discovery flow](../../assets/demo/dice-source.gif)

Use this guide when wiring a public Dice careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Dice

Dice is a major US tech job board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "dice-jobs",
    "source_type": "dice",
    "base_url": "https://www.dice.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Positions | `/positions/70113` |
| Jobs | `/jobs/77224` |
| Job | `/job/83335` |
| Listings | `/listings/94446` |
| Tech Jobs | `/tech-jobs/105557` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
