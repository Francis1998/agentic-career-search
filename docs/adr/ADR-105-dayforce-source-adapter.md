# ADR-105: Dayforce (Ceridian) Public Careers Source Adapter

**Date:** 2026-07-31
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Dayforce (Ceridian) is an enterprise HCM platform whose public career sites
commonly expose listing pages with detail hrefs under `/JobDetail/{id}`,
`/careers/job/{id}`, `/MyCareer/JobDetail?jobId={id}`, and `/positions/{id}`.

The existing HTML adapters (Avature, JobScore, Eightfold) already use
deterministic URL-shape matching instead of brittle CSS-only scraping. Dayforce
fits that pattern. Keeping discovery on the public HTML board avoids depending
on authenticated Dayforce APIs and stays aligned with the shared adapter
contract in ADR-077.

## Decision

Add a `DayforceAdapter` (`source_type = "dayforce"`) that:

1. Recognises `/JobDetail/{id}` posting detail hrefs.
2. Accepts `/careers/job/{id}` detail shapes.
3. Accepts `/MyCareer/JobDetail?jobId={id}` query forms.
4. Accepts `/positions/{id}` and `/position/{id}` vanity shapes.
5. Rejects board indexes plus apply/login/signin/application paths.
6. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
7. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Dayforce-hosted public boards are covered without authenticated Dayforce APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
