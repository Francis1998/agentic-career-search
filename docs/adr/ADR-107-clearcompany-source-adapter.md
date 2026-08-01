# ADR-107: ClearCompany Public Careers Source Adapter

**Date:** 2026-08-01
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

ClearCompany is an applicant tracking system used by mid-market employers and
staffing firms. Its public career sites commonly host listing pages with detail
pages under `/careers/job/{id}`, `/careers/{id}`, `/jobs/{id}`,
`/job/{id}-{slug}`, and `/position/{id}`.

The existing HTML adapters (Homerun, Hireology, Dayforce) already use
deterministic URL-shape matching instead of brittle CSS-only scraping. ClearCompany
fits that pattern. Keeping discovery on the public HTML board avoids depending
on authenticated ClearCompany APIs and stays aligned with the shared adapter
contract in ADR-077.

## Decision

Add a `ClearCompanyAdapter` (`source_type = "clearcompany"`) that:

1. Recognises `/careers/job/{id}` posting detail hrefs.
2. Accepts `/careers/{id}` vanity shapes (excluding `/careers/job` index).
3. Accepts `/jobs/{id}` and `/position/{id}` paths.
4. Accepts `/job/{id}-{slug}` slug-id shapes.
5. Rejects board indexes plus apply/login/signin/application/about paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- ClearCompany-hosted public boards are covered without authenticated APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
