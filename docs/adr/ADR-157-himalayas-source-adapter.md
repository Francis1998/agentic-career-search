# ADR-157: Himalayas Public Careers Source Adapter

**Date:** 2026-08-23
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Himalayas publishes remote job boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /companies/{slug}/jobs/{id},
/remote-jobs/{id}, or /roles/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. Himalayas fits that pattern: public HTML discovery
avoids authenticated APIs and stays aligned with the shared adapter contract
in ADR-077. Popular remote job aggregators (Remotive, Himalayas, Working
Nomads) are common sources in JobSpy-style scrapers; the agent still needs a
first-party deterministic adapter under the shared contract.

## Decision

Add a `HimalayasAdapter` (`source_type = "himalayas"`) that:

1. Recognises the URL shapes `/jobs/{id}`, `/job/{id}`,
   `/companies/{slug}/jobs/{id}`, `/remote-jobs/{id}`, `/roles/{id}`.
2. Rejects board indexes, bare company pages, plus apply/login/signin/
   application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Himalayas public recruiting boards are covered without authenticated APIs or
  headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
