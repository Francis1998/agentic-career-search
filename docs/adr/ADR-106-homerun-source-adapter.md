# ADR-106: Homerun Public Careers Source Adapter

**Date:** 2026-07-31
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Homerun is an applicant tracking system used by European startups and scale-ups.
Its public career sites commonly host listing pages at `{company}.homerun.co` with
detail pages under `/jobs/{id}-{slug}`, `/o/{id}`, and `/vacancies/{id}`.

The existing HTML adapters (Teamtailor, JobScore, Avature) already use
deterministic URL-shape matching instead of brittle CSS-only scraping. Homerun
fits that pattern. Keeping discovery on the public HTML board avoids depending
on authenticated Homerun APIs and stays aligned with the shared adapter
contract in ADR-077.

## Decision

Add a `HomerunAdapter` (`source_type = "homerun"`) that:

1. Recognises `/jobs/{id}-{slug}` posting detail hrefs.
2. Accepts `/o/{id}` short-opening shapes.
3. Accepts `/vacancies/{id}` and `/vacancy/{id}` vanity shapes.
4. Rejects board indexes plus apply/login/signin/application/about paths.
5. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
6. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Homerun-hosted public boards are covered without authenticated Homerun APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
