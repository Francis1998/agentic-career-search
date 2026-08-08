# ADR-117: Loxo Public Careers Source Adapter

**Date:** 2026-08-06
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Loxo is an applicant tracking platform popular with recruiting agencies and
growth-stage companies. Its public career sites commonly host listing pages with
detail pages under `/jobs/{id}`, `/job/{id}`, `/positions/{id}`, `/careers/{id}`,
and `/careers/job/{id}`.

The existing HTML adapters (Softgarden, Manatal, Factorial) already use
deterministic URL-shape matching instead of brittle CSS-only scraping. Loxo fits
that pattern. Keeping discovery on the public HTML board avoids depending on
authenticated Loxo APIs and stays aligned with the shared adapter contract in
ADR-077.

## Decision

Add a `LoxoAdapter` (`source_type = "loxo"`) that:

1. Recognises `/jobs/{id}` plural paths.
2. Accepts `/job/{id}` singular paths.
3. Accepts `/positions/{id}` positions paths.
4. Accepts `/careers/{id}` and `/careers/job/{id}` careers paths.
5. Rejects board indexes plus apply/login/signin/application/about paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Loxo-hosted public boards are covered without authenticated APIs or
  headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
