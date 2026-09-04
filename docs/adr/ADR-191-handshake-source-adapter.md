# ADR-191: Handshake Public Careers Source Adapter

**Date:** 2026-09-04
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Handshake publishes career boards whose public listings commonly link to
detail pages under /jobs/{id}, /job-search/{id}, /postings/{id}, /edu/jobs/{id}, /internship/{id}.

Handshake is the leading university career marketplace covered by modern job scrapers but missing from this repository's adapter set; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `HandshakeAdapter` (`source_type = "handshake"`) that:

1. Recognises the URL shapes /jobs/{id}, /job-search/{id}, /postings/{id}, /edu/jobs/{id}, /internship/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Handshake public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
