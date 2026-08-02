# ADR-112: Join Public Careers Source Adapter

**Date:** 2026-08-02
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Join is an applicant tracking system used by European startups and scale-ups.
Its public career sites commonly host listing pages with detail pages under
`/companies/{slug}/jobs/{id}`, `/jobs/{id}`, `/job/{id}`, and
`/positions/{id}`.

The existing HTML adapters (Recruiterflow, ClearCompany, Softgarden) already
use deterministic URL-shape matching instead of brittle CSS-only scraping. Join
fits that pattern. Keeping discovery on the public HTML board avoids depending on
authenticated Join APIs and stays aligned with the shared adapter contract in
ADR-077.

## Decision

Add a `JoinAdapter` (`source_type = "join"`) that:

1. Recognises `/companies/{slug}/jobs/{id}` company-scoped posting hrefs.
2. Accepts `/jobs/{id}` plural paths.
3. Accepts `/job/{id}` singular paths.
4. Accepts `/positions/{id}` position paths.
5. Rejects board indexes plus apply/login/signin/application/about paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Join-hosted public boards are covered without authenticated APIs or headless
  browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
