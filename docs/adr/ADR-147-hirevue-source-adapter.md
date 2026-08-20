# ADR-147: HireVue Public Careers Source Adapter

**Date:** 2026-08-20
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

HireVue is a hiring platform whose public career pages commonly link to detail
pages under `/jobs/{id}`, `/job/{id}`, `/careers/{id}`,
`/careers/job/{id}`, or `/requisition/{id}`.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. HireVue fits that pattern: public HTML discovery
avoids authenticated APIs and stays aligned with the shared adapter contract
in ADR-077. JobSpy and Greenhouse-style API clients cover common ATS boards,
but leave gaps for employer-hosted HireVue career pages.

## Decision

Add a `HireVueAdapter` (`source_type = "hirevue"`) that:

1. Recognises the URL shapes listed above.
2. Rejects board indexes plus apply/login/signin/application/about paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- HireVue-hosted public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
