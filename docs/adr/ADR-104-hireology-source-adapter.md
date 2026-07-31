# ADR-104: Hireology Public Careers Source Adapter

**Date:** 2026-07-31
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Hireology is an applicant tracking system used by franchise, retail, and
multi-location hiring teams. Its public career sites commonly host listing pages
at `careers.hireology.com/{company}` with detail pages under `/jobs/{id}`,
`/careers/job/{id}`, and `/job/{id}/{slug}`.

The existing HTML adapters (JobScore, Avature, Gem) already use deterministic
URL-shape matching instead of brittle CSS-only scraping. Hireology fits that
pattern. Keeping discovery on the public HTML board avoids depending on
authenticated Hireology APIs and stays aligned with the shared adapter contract
in ADR-077.

## Decision

Add a `HireologyAdapter` (`source_type = "hireology"`) that:

1. Recognises `/jobs/{id}` posting detail hrefs.
2. Accepts `/careers/job/{id}` detail shapes.
3. Accepts `/job/{id}/{slug}` vanity shapes.
4. Rejects board indexes plus apply/login/signin/application/about paths.
5. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
6. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Hireology-hosted public boards are covered without authenticated Hireology APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
