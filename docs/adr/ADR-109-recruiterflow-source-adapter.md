# ADR-109: Recruiterflow Public Careers Source Adapter

**Date:** 2026-08-01
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Recruiterflow is an applicant tracking system used by recruiting agencies and
growing companies. Its public career sites commonly host listing pages with
detail pages under `/jobs/{id}`, `/job/{id}`, `/careers/job/{id}`,
`/openings/{id}`, and `/opening/{id}`.

The existing HTML adapters (Homerun, Hireology, Dayforce) already use
deterministic URL-shape matching instead of brittle CSS-only scraping.
Recruiterflow fits that pattern. Keeping discovery on the public HTML board
avoids depending on authenticated Recruiterflow APIs and stays aligned with the
shared adapter contract in ADR-077.

## Decision

Add a `RecruiterflowAdapter` (`source_type = "recruiterflow"`) that:

1. Recognises `/jobs/{id}` posting detail hrefs.
2. Accepts `/job/{id}` singular paths.
3. Accepts `/careers/job/{id}` nested career paths.
4. Accepts `/openings/{id}` and `/opening/{id}` vanity shapes.
5. Rejects board indexes plus apply/login/signin/application/about paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Recruiterflow-hosted public boards are covered without authenticated APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
