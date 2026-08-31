# Levels.fyi Source Guide

![Levels.fyi discovery flow](../../assets/demo/levelsfyi-source.gif)

Use this guide when wiring a public Levels.fyi careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Levels.fyi

Levels.fyi is a popular compensation and tech roles board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "levelsfyi-jobs",
    "source_type": "levelsfyi",
    "base_url": "https://www.levels.fyi/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/70113` |
| Job | `/job/77224` |
| Roles | `/roles/83335` |
| Openings | `/openings/94446` |
| Levels | `/levels/105557` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
