# ADR-114: UKG Public Careers Source Adapter

**Date:** 2026-08-03
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

UKG is a widely used applicant tracking / HR platform. Its public
career sites commonly host listing pages with detail pages under `/jobs/{id}`, `/job/{id}`, `/opportunities/{id}`, `/opportunity/{id}`, `/careers/job/{id}`.

The existing HTML adapters (Softgarden, Factorial, Manatal) already use
deterministic URL-shape matching instead of brittle CSS-only scraping.
UKG fits that pattern. Keeping discovery on the public HTML board
avoids depending on authenticated APIs and stays aligned with ADR-077.

## Decision

Add a `UkgAdapter` (`source_type = "ukg"`) that:

1. Recognises `/jobs/{id}` paths.
2. Recognises `/job/{id}` paths.
3. Recognises `/opportunities/{id}` paths.
4. Recognises `/opportunity/{id}` paths.
5. Recognises `/careers/job/{id}` paths.
6. Rejects board indexes plus apply/login/signin/application/about paths.
7. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
8. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- UKG-hosted public boards are covered without authenticated APIs or
  headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
