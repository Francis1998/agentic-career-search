# ADR-162: Dynamite Jobs Public Careers Source Adapter

**Date:** 2026-08-26
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Dynamite Jobs publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /remote-jobs/{id}, /positions/{id}, /listings/{id}.

Inspired by remote job board aggregators (Himalayas/Remotive-style boards); this repo's board adapters left Dynamite Jobs without deterministic HTML discovery under ADR-077.

## Decision

Add a `DynamitejobsAdapter` (`source_type = "dynamitejobs"`) that:

1. Recognises the URL shapes /jobs/{id}, /job/{id}, /remote-jobs/{id}, /positions/{id}, /listings/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Dynamite Jobs public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
