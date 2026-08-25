# ADR-161: Jobspresso Public Careers Source Adapter

**Date:** 2026-08-25
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Jobspresso publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /remote-jobs/{id}, /postings/{id}, /openings/{id}.

Remote marketplace scrapers commonly include Jobspresso; this repo's board adapters left Jobspresso without deterministic HTML discovery under ADR-077.

## Decision

Add a `JobspressoAdapter` (`source_type = "jobspresso"`) that:

1. Recognises the URL shapes `/jobs/{id}`, `/job/{id}`, `/remote-jobs/{id}`, `/postings/{id}`, `/openings/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Jobspresso public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
