# ADR-108: Applied Public Careers Source Adapter

**Date:** 2026-08-01
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Applied is a modern applicant tracking system used by startups and scale-ups.
Its public career sites commonly host listing pages with detail pages under
`/jobs/{id}`, `/j/{id}`, `/role/{id}`, `/roles/{id}`, and `/job/{id}`.
Applied.co boards often use `/jobs/{uuid-or-slug}` for posting identifiers.

The existing HTML adapters (Homerun, Hireology, Dayforce) already use
deterministic URL-shape matching instead of brittle CSS-only scraping. Applied
fits that pattern. Keeping discovery on the public HTML board avoids depending
on authenticated Applied APIs and stays aligned with the shared adapter
contract in ADR-077.

## Decision

Add an `AppliedAdapter` (`source_type = "applied"`) that:

1. Recognises `/jobs/{id}` posting detail hrefs (uuid or slug ids).
2. Accepts `/j/{id}` short-form paths.
3. Accepts `/role/{id}` and `/roles/{id}` vanity shapes.
4. Accepts `/job/{id}` singular paths.
5. Rejects board indexes plus apply/login/signin/application/about paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Applied-hosted public boards are covered without authenticated APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
