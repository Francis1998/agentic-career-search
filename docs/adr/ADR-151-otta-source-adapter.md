# ADR-151: Otta Public Careers Source Adapter

**Date:** 2026-08-21
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Otta is a UK/EU tech careers marketplace whose public listing pages commonly link to detail pages under /jobs/{id}, /job/{id}, /roles/{id}, /role/{id}, or /openings/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. Otta fits that pattern: public HTML
discovery avoids authenticated APIs and stays aligned with the shared adapter
contract in ADR-077. Popular scrapers such as JobSpy emphasize aggregator boards and leave Otta employer/marketplace detail pages undercovered.

## Decision

Add a `OttaAdapter` (`source_type = "otta"`) that:

1. Recognises the URL shapes `/jobs/{id}`, `/job/{id}`, `/roles/{id}`, `/role/{id}`, `/openings/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Otta-hosted public recruiting boards are covered without
  authenticated APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
