# ADR-159: JustRemote Public Careers Source Adapter

**Date:** 2026-08-25
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

JustRemote publishes career boards whose public listings commonly link to
detail pages under /remote-jobs/{id}, /jobs/{id}, /job/{id}, /listings/{id}, /listing/{id}.

JobSpy-style remote aggregators cover JustRemote boards, but this repo's ATS-focused adapters left JustRemote marketplace boards without deterministic HTML discovery under ADR-077.

## Decision

Add a `JustremoteAdapter` (`source_type = "justremote"`) that:

1. Recognises the URL shapes `/remote-jobs/{id}`, `/jobs/{id}`, `/job/{id}`, `/listings/{id}`, `/listing/{id}`.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- JustRemote public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
