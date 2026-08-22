# ADR-154: WeWorkRemotely Public Careers Source Adapter

**Date:** 2026-08-22
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

WeWorkRemotely publishes remote job boards whose public listings commonly link
to detail pages under /remote-jobs/{id}, /jobs/{id}, /job/{id}, /listings/{id},
or /listing/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. WeWorkRemotely fits that pattern: public HTML
discovery avoids authenticated APIs and stays aligned with the shared adapter
contract in ADR-077. Aggregator-oriented scrapers leave WWR employer listing
detail pages undercovered for first-party deterministic discovery.

## Decision

Add a `WeworkremotelyAdapter` (`source_type = "weworkremotely"`) that:

1. Recognises the URL shapes `/remote-jobs/{id}`, `/jobs/{id}`, `/job/{id}`,
   `/listings/{id}`, `/listing/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- WeWorkRemotely public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
