# Work at a Startup Source Guide

![Work at a Startup discovery flow](../../assets/demo/workatastartup-source.gif)

Use this guide when wiring a public Work at a Startup careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 is optional
and runs after candidates are collected.

## Why Work at a Startup

YC Work at a Startup is a high-signal startup-jobs gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "workatastartup-jobs",
    "source_type": "workatastartup",
    "base_url": "https://www.workatastartup.com/jobs"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Companies | `/companies/50113` |
| Startups | `/startups/57224` |
| Roles | `/roles/63335` |
| Jobs | `/jobs/74446` |
| Job | `/job/85557` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
