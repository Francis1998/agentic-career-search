# ADR-185: TheMuse Public Careers Source Adapter

**Date:** 2026-09-02
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

TheMuse publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /positions/{id}, /openings/{id}, /roles/{id}.

The Muse is a popular career/content job board missing from many open-source scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `ThemuseAdapter` (`source_type = "themuse"`) that:

1. Recognises the URL shapes /jobs/{id}, /job/{id}, /positions/{id}, /openings/{id}, /roles/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- TheMuse public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
