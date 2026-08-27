# ADR-166: Authentic Jobs Public Careers Source Adapter

**Date:** 2026-08-27
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Authentic Jobs publishes career boards whose public listings commonly link to
detail pages under /postings/{id}, /listing/{id}, /opportunities/{id}, /jobs/{id}, /job/{id}.

Authentic Jobs is a design/creative hiring board gap relative to jobSpy/RemoteOK scrapers; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `AuthenticjobsAdapter` (`source_type = "authenticjobs"`) that:

1. Recognises the URL shapes /postings/{id}, /listing/{id}, /opportunities/{id}, /jobs/{id}, /job/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Authentic Jobs public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
