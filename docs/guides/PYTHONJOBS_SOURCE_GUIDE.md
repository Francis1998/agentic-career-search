# Python Jobs Source Guide

![Python Jobs discovery flow](../../assets/demo/pythonjobs-source.gif)

Use this guide when wiring a public Python Jobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Python Jobs

Python.org Jobs is a high-signal Python-language board gap vs JobSpy aggregators that focus on Indeed/LinkedIn; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "pythonjobs-jobs",
    "source_type": "pythonjobs",
    "base_url": "https://www.python.org/jobs/"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Python Jobs | `/python-jobs/49102` |
| Listings | `/listings/56213` |
| Positions | `/positions/62324` |
| Jobs | `/jobs/73435` |
| Job | `/job/84546` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
