# ADR-188: Indeed Public Careers Source Adapter

**Date:** 2026-09-03
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Indeed publishes career boards whose public listings commonly link to
detail pages under /viewjob/{id}, /jobs/{id}, /job/{id}, /rc/clk/{id}, /m/jobs/{id}.

Indeed is a widely-used aggregator job board missing from this repository's
adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add an `IndeedAdapter` (`source_type = "indeed"`) that:

1. Recognises the URL shapes /viewjob/{id}, /jobs/{id}, /job/{id}, /rc/clk/{id}, /m/jobs/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Indeed public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
