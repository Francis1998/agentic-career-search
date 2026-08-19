# ADR-146: Jibe Public Careers Source Adapter

**Date:** 2026-08-19
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Jibe is an employer-brand / ATS careers platform whose public
boards commonly host listing pages with detail pages under `/jobs/{id}`, `/job/{id}`, `/position/{id}`, `/positions/{id}`, `/requisition/{id}`.

The existing HTML adapters (ADP, Paradox, Catsone) use deterministic URL-shape
matching instead of brittle CSS-only scraping. Jibe fits that
pattern. Keeping discovery on the public HTML board avoids depending on
authenticated APIs and stays aligned with the shared adapter contract in
ADR-077. Similar open-source job scrapers (JobSpy, board-specific Greenhouse
API clients) cover a subset of ATS brands; this adapter extends coverage for
enterprise career sites commonly missing from those tools.

## Decision

Add a `JibeAdapter` (`source_type = "jibe"`) that:

1. Recognises the URL shapes listed above.
2. Rejects board indexes plus apply/login/signin/application/about paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Jibe-hosted public recruiting boards are covered without
  authenticated APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
