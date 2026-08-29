# ADR-171: 4 Day Week Public Careers Source Adapter

**Date:** 2026-08-29
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

4 Day Week publishes career boards whose public listings commonly link to
detail pages under /four-day/{id}, /listings/{id}, /positions/{id}, /jobs/{id}, /job/{id}.

4 Day Week (4dayweek.io) is a compressed-week remote board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `FourdayweekAdapter` (`source_type = "fourdayweek"`) that:

1. Recognises the URL shapes /four-day/{id}, /listings/{id}, /positions/{id}, /jobs/{id}, /job/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- 4 Day Week public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
