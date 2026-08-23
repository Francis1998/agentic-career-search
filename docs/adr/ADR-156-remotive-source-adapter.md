# ADR-156: Remotive Public Careers Source Adapter

**Date:** 2026-08-23
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Remotive publishes remote job boards whose public listings commonly link to
detail pages under /remote-jobs/{id}, /remote-job/{id}, /jobs/{id}, /job/{id},
or /positions/{id}.

The existing HTML adapters use deterministic URL-shape matching instead of
brittle CSS-only scraping. Remotive fits that pattern: public HTML discovery
avoids authenticated APIs and stays aligned with the shared adapter contract
in ADR-077. JobSpy and similar scrapers emphasize Remotive as an aggregator,
but the agent still needs a first-party deterministic adapter under the shared
contract.

## Decision

Add a `RemotiveAdapter` (`source_type = "remotive"`) that:

1. Recognises the URL shapes `/remote-jobs/{id}`, `/remote-job/{id}`,
   `/jobs/{id}`, `/job/{id}`, `/positions/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Remotive public recruiting boards are covered without authenticated APIs or
  headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
