# ADR-158: Working Nomads Public Careers Source Adapter

**Date:** 2026-08-23
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Working Nomads publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /remote-jobs/{id}, /positions/{id},
or /position/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. Working Nomads fits that pattern: public HTML
discovery avoids authenticated APIs and stays aligned with the shared adapter
contract in ADR-077. Marketplace/aggregator scrapers leave Working Nomads
detail pages undercovered for first-party deterministic discovery.

## Decision

Add a `WorkingnomadsAdapter` (`source_type = "workingnomads"`) that:

1. Recognises the URL shapes `/jobs/{id}`, `/job/{id}`, `/remote-jobs/{id}`,
   `/positions/{id}`, `/position/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Working Nomads public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
