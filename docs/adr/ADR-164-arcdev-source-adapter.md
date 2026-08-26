# ADR-164: Arc.dev Public Careers Source Adapter

**Date:** 2026-08-26
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Arc.dev publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /roles/{id}, /positions/{id}, /openings/{id}.

Arc.dev (formerly CodementorX) is a remote tech hiring board gap; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `ArcdevAdapter` (`source_type = "arcdev"`) that:

1. Recognises the URL shapes /jobs/{id}, /job/{id}, /roles/{id}, /positions/{id}, /openings/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Arc.dev public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
