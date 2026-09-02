# ADR-183: ZipRecruiter Public Careers Source Adapter

**Date:** 2026-09-02
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

ZipRecruiter publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job/{id}, /listings/{id}, /openings/{id}, /positions/{id}.

ZipRecruiter is a major US job board covered by JobSpy-style aggregators but missing here; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `ZiprecruiterAdapter` (`source_type = "ziprecruiter"`) that:

1. Recognises the URL shapes /jobs/{id}, /job/{id}, /listings/{id}, /openings/{id}, /positions/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- ZipRecruiter public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
