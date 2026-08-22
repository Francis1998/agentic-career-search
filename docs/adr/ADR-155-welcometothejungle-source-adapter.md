# ADR-155: Welcome to the Jungle Public Careers Source Adapter

**Date:** 2026-08-22
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Welcome to the Jungle (WTTJ) publishes career boards whose public listings
commonly link to detail pages under /jobs/{id}, /job/{id},
/companies/{slug}/jobs/{id}, /offers/{id}, or /offer/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. WTTJ fits that pattern: public HTML discovery
avoids authenticated APIs and stays aligned with the shared adapter contract
in ADR-077. Marketplace/aggregator scrapers leave WTTJ company and offer
detail pages undercovered for first-party deterministic discovery.

## Decision

Add a `WelcometothejungleAdapter` (`source_type = "welcometothejungle"`) that:

1. Recognises the URL shapes `/jobs/{id}`, `/job/{id}`,
   `/companies/{slug}/jobs/{id}`, `/offers/{id}`, `/offer/{id}`.
2. For `/companies/{slug}/jobs/{id}`, extracts `{id}` as the external id.
3. Rejects board indexes plus apply/login/signin/application/about/index paths
   and bare company pages.
4. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
5. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Welcome to the Jungle public recruiting boards are covered without
  authenticated APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
