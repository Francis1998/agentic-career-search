# ADR-172: AI Jobs Public Careers Source Adapter

**Date:** 2026-08-29
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

AI Jobs publishes career boards whose public listings commonly link to
detail pages under /ai-jobs/{id}, /roles/{id}, /openings/{id}, /jobs/{id}, /job/{id}.

AI Jobs (ai-jobs.net) covers ML/LLM roles that generic remote boards miss; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `AijobsAdapter` (`source_type = "aijobs"`) that:

1. Recognises the URL shapes /ai-jobs/{id}, /roles/{id}, /openings/{id}, /jobs/{id}, /job/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- AI Jobs public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
