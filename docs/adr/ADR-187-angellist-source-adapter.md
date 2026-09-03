# ADR-187: AngelList (Wellfound) Public Careers Source Adapter

**Date:** 2026-09-03
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

AngelList publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /startups/{id}, /startup-jobs/{id}, /roles/{id}, /positions/{id}.

AngelList (Wellfound) is a prominent startup job board missing from many open-source scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add an `AngellistAdapter` (`source_type = "angellist"`) that:

1. Recognises the URL shapes /jobs/{id}, /startups/{id}, /startup-jobs/{id}, /roles/{id}, /positions/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- AngelList public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
