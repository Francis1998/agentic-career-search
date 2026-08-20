# ADR-149: Yello Public Careers Source Adapter

**Date:** 2026-08-20
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Yello is a recruiting and early-talent platform whose public career pages
commonly link to detail pages under `/jobs/{id}`, `/job/{id}`,
`/position/{id}`, `/positions/{id}`, or `/opening/{id}`.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. Yello fits that pattern: public HTML discovery
avoids authenticated APIs and stays aligned with the shared adapter contract
in ADR-077. JobSpy and Greenhouse-style API clients cover common ATS boards,
but leave gaps for employer-hosted Yello career pages.

## Decision

Add a `YelloAdapter` (`source_type = "yello"`) that:

1. Recognises the URL shapes listed above.
2. Rejects board indexes plus apply/login/signin/application/about paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Yello-hosted public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
