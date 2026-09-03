# ADR-186: Glassdoor Public Careers Source Adapter

**Date:** 2026-09-03
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Glassdoor publishes career boards whose public listings commonly link to
detail pages under /reviews/{id}, /jobs/{id}, /job-listing/{id}, /positions/{id}, /openings/{id}.

Glassdoor is a widely-used employer review and job board missing from many open-source scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `GlassdoorAdapter` (`source_type = "glassdoor"`) that:

1. Recognises the URL shapes /reviews/{id}, /jobs/{id}, /job-listing/{id}, /positions/{id}, /openings/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Glassdoor public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
