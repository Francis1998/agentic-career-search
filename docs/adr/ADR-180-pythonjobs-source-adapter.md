# ADR-180: Python Jobs Public Careers Source Adapter

**Date:** 2026-09-01
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Python Jobs publishes career boards whose public listings commonly link to
detail pages under /python-jobs/{id}, /listings/{id}, /positions/{id}, /jobs/{id}, /job/{id}.

Python.org Jobs is a high-signal Python-language board gap vs JobSpy aggregators that focus on Indeed/LinkedIn; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `PythonjobsAdapter` (`source_type = "pythonjobs"`) that:

1. Recognises the URL shapes /python-jobs/{id}, /listings/{id}, /positions/{id}, /jobs/{id}, /job/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Python Jobs public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
