# ADR-110: Manatal Public Careers Source Adapter

**Date:** 2026-08-02
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Manatal is an applicant tracking system used by recruiting agencies and
growing companies. Its public career sites commonly host listing pages with
detail pages under `/jobs/{id}`, `/job/{id}`, `/careers/{id}`,
`/careers/job/{id}`, and `/openings/{id}`.

The existing HTML adapters (Recruiterflow, ClearCompany, Homerun) already use
deterministic URL-shape matching instead of brittle CSS-only scraping.
Manatal fits that pattern. Keeping discovery on the public HTML board avoids
depending on authenticated Manatal APIs and stays aligned with the shared
adapter contract in ADR-077.

## Decision

Add a `ManatalAdapter` (`source_type = "manatal"`) that:

1. Recognises `/jobs/{id}` posting detail hrefs.
2. Accepts `/job/{id}` singular paths.
3. Accepts `/careers/{id}` vanity shapes (excluding `/careers/job` index).
4. Accepts `/careers/job/{id}` nested career paths.
5. Accepts `/openings/{id}` vanity shapes.
6. Rejects board indexes plus apply/login/signin/application/about paths.
7. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
8. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Manatal-hosted public boards are covered without authenticated APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
