# ADR-111: Softgarden Public Careers Source Adapter

**Date:** 2026-08-02
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Softgarden is an applicant tracking system widely used by European employers.
Its public career sites commonly host listing pages with detail pages under
`/job/{id}`, `/jobs/{id}`, `/vacancies/{id}`, `/vacancy/{id}`, and
`/position/{id}`.

The existing HTML adapters (ClearCompany, Recruiterflow, Homerun) already use
deterministic URL-shape matching instead of brittle CSS-only scraping.
Softgarden fits that pattern. Keeping discovery on the public HTML board avoids
depending on authenticated Softgarden APIs and stays aligned with the shared
adapter contract in ADR-077.

## Decision

Add a `SoftgardenAdapter` (`source_type = "softgarden"`) that:

1. Recognises `/job/{id}` posting detail hrefs.
2. Accepts `/jobs/{id}` plural paths.
3. Accepts `/vacancies/{id}` and `/vacancy/{id}` vacancy shapes.
4. Accepts `/position/{id}` position paths.
5. Rejects board indexes plus apply/login/signin/application/about paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Softgarden-hosted public boards are covered without authenticated APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
