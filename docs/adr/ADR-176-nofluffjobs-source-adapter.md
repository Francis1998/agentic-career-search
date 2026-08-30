# ADR-176: No Fluff Jobs Public Careers Source Adapter

**Date:** 2026-08-30
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

No Fluff Jobs publishes career boards whose public listings commonly link to
detail pages under /pl/{id}, /job/{id}, /offers/{id}, /positions/{id}, /jobs/{id}.

No Fluff Jobs is a popular EU tech board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `NofluffjobsAdapter` (`source_type = "nofluffjobs"`) that:

1. Recognises the URL shapes /pl/{id}, /job/{id}, /offers/{id}, /positions/{id}, /jobs/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- No Fluff Jobs public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
