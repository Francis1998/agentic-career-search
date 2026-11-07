# Crypto Jobs Source Guide

![Crypto Jobs discovery flow](../../assets/demo/cryptojobs-source.gif)

Use this guide when wiring a public Crypto Jobs careers board into
**agentic-career-search**. Discovery is deterministic HTML URL-shape matching;
enrichment with GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro is optional
and runs after candidates are collected.

## Why Crypto Jobs

Crypto Jobs List is a Web3/crypto hiring board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Usage

```bash
curl -X POST localhost:8000/source-configs \
  -H 'content-type: application/json' \
  -d '{
    "name": "cryptojobs-jobs",
    "source_type": "cryptojobs",
    "base_url": "https://cryptojobslist.com"
  }'
```

## URL shapes

| Shape | Example |
|---|---|
| Crypto Jobs | `/crypto-jobs/60113` |
| Web3 | `/web3/67224` |
| Positions | `/positions/73335` |
| Jobs | `/jobs/84446` |
| Job | `/job/95557` |

Board index pages, apply/login steps, about/index links, and navigation links
are ignored.

## Safety

- Public HTML only — no authenticated APIs or credential storage.
- Apply/login/signin/about/index paths are excluded from discovery.
- Optional LLM enrichment is bounded by the shared safety policy.
