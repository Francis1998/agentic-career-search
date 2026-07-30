# ADR-101: JobScore Public Careers Source Adapter

**Date:** 2026-07-30
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

JobScore is an applicant tracking system used by mid-market and growth hiring
teams. Its public career sites are commonly hosted at
`careers.jobscore.com/careers/{company}` with detail pages under
`/careers/{company}/jobs/{slug}-{id}` or `/careers/{company}/jobs/{id}`, and
some tenants also expose `/jobs/{id}`, `/jobs/{slug}/{id}`, `/position/{id}`,
and `/positions/{id}` shapes on `*.jobscore.com` domains.

The existing HTML adapters (Gem, Fountain, Teamtailor, Pinpoint) already use
deterministic URL-shape matching instead of brittle CSS-only scraping. JobScore
fits that pattern. Keeping discovery on the public HTML board avoids depending
on authenticated JobScore APIs and stays aligned with the shared adapter
contract in ADR-077.

## Decision

Add a `JobScoreAdapter` (`source_type = "jobscore"`) that:

1. Recognises `/careers/{company}/jobs/{slug}-{id}` and
   `/careers/{company}/jobs/{id}` posting detail hrefs.
2. Accepts alternate detail shapes `/jobs/{id}` and `/jobs/{slug}/{id}`.
3. Accepts `/position/{id}` and `/positions/{id}` vanity shapes.
4. Rejects board indexes plus apply/login/signin/application/about paths.
5. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
6. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- JobScore-hosted public boards are covered without authenticated JobScore APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
