# ADR-152: Built In Public Careers Source Adapter

**Date:** 2026-08-21
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Built In publishes city and national tech career boards whose public listings commonly link to detail pages under /job/{id}, /jobs/{id}, /company-jobs/{id}, /careers/job/{id}, or /role/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. Built In fits that pattern: public HTML
discovery avoids authenticated APIs and stays aligned with the shared adapter
contract in ADR-077. ATS-focused adapters leave Built In city boards (similar to RemoteOK/WWR aggregator gaps) without deterministic HTML discovery.

## Decision

Add a `BuiltinAdapter` (`source_type = "builtin"`) that:

1. Recognises the URL shapes `/job/{id}`, `/jobs/{id}`, `/company-jobs/{id}`, `/careers/job/{id}`, `/role/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Built In-hosted public recruiting boards are covered without
  authenticated APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
