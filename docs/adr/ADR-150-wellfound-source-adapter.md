# ADR-150: Wellfound Public Careers Source Adapter

**Date:** 2026-08-21
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Wellfound (formerly AngelList Talent) is a startup hiring platform whose public career pages commonly link to detail pages under /jobs/{id}, /job/{id}, /role/{id}, /roles/{id}, or /startup-jobs/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. Wellfound fits that pattern: public HTML
discovery avoids authenticated APIs and stays aligned with the shared adapter
contract in ADR-077. JobSpy and Greenhouse-style API clients cover common ATS boards, but leave gaps for Wellfound/AngelList public startup job pages.

## Decision

Add a `WellfoundAdapter` (`source_type = "wellfound"`) that:

1. Recognises the URL shapes `/jobs/{id}`, `/job/{id}`, `/role/{id}`, `/roles/{id}`, `/startup-jobs/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Wellfound-hosted public recruiting boards are covered without
  authenticated APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
