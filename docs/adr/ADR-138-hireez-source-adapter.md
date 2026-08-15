# ADR-138: HireEZ / Hiretual Public Careers Source Adapter

**Date:** 2026-08-15
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

HireEZ (formerly Hiretual) is an applicant tracking / recruiting platform whose
public career sites commonly host listing pages with detail pages under
`/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
`/positions/{id}`.

The existing HTML adapters (Beamery, Eploy, Tribepad) already use deterministic
URL-shape matching instead of brittle CSS-only scraping. HireEZ fits that
pattern. Keeping discovery on the public HTML board avoids depending on
authenticated HireEZ APIs and stays aligned with the shared adapter contract
in ADR-077.

## Decision

Add a `HireezAdapter` (`source_type = "hireez"`) that:

1. Recognises `/jobs/{id}` plural paths.
2. Accepts `/job/{id}` singular paths.
3. Accepts `/careers/{id}` and `/careers/job/{id}` careers paths.
4. Accepts `/positions/{id}` positions paths.
5. Rejects board indexes plus apply/login/signin/application/about paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- HireEZ-hosted public boards are covered without authenticated APIs or
  headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
