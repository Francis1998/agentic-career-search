# Work in the Open Source Guide

![Work in the Open discovery flow](../../assets/demo/workintheopen-source.gif)

Use this guide when wiring a public Work in the Open careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Work in the Open

Work in the Open is a remote-friendly open-company board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "workintheopen-jobs",
    "source_type": "workintheopen",
    "base_url": "https://workintheopen.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Jobs | `/jobs/70113` |
| Job | `/job/77224` |
| Roles | `/roles/83335` |
| Openings | `/openings/94446` |
| Positions | `/positions/105557` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
