# ADR-160: NoDesk Public Careers Source Adapter

**Date:** 2026-08-25
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

NoDesk publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /remote/{id}, /positions/{id}, /careers/{id}.

Popular remote-job scrapers (JobSpy / similar) index NoDesk listings; this repo lacked a first-party deterministic NoDesk HTML adapter under ADR-077.

## Decision

Add a `NodeskAdapter` (`source_type = "nodesk"`) that:

1. Recognises the URL shapes `/jobs/{id}`, `/job/{id}`, `/remote/{id}`, `/positions/{id}`, `/careers/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- NoDesk public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
