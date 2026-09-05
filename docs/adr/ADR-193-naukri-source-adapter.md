# ADR-193: Naukri Public Careers Source Adapter

**Date:** 2026-09-05
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Naukri publishes career boards whose public listings commonly link to
detail pages under /job-listings/{id}, /jobdetail/{id}, /jobs/{id}, /job-description/{id}, /recruiters/job/{id}.

Naukri is India's largest job board covered by JobSpy-style scrapers but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `NaukriAdapter` (`source_type = "naukri"`) that:

1. Recognises the URL shapes /job-listings/{id}, /jobdetail/{id}, /jobs/{id}, /job-description/{id}, /recruiters/job/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Naukri public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
