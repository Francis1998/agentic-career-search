# ADR-190: CareerBuilder Public Careers Source Adapter

**Date:** 2026-09-04
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

CareerBuilder publishes career boards whose public listings commonly link to
detail pages under /job/{id}, /jobs/{id}, /jobseeker/jobs/{id}, /share/job/{id}, /career-jobs/{id}.

CareerBuilder is a major US job board present in JobSpy-style aggregators but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `CareerbuilderAdapter` (`source_type = "careerbuilder"`) that:

1. Recognises the URL shapes /job/{id}, /jobs/{id}, /jobseeker/jobs/{id}, /share/job/{id}, /career-jobs/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- CareerBuilder public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
