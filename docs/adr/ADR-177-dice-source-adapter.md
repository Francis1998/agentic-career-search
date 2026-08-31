# ADR-177: Dice Public Careers Source Adapter

**Date:** 2026-08-31
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Dice publishes career boards whose public listings commonly link to
detail pages under /positions/{id}, /jobs/{id}, /job/{id}, /listings/{id}, /tech-jobs/{id}.

Dice is a major US tech job board gap vs JobSpy-style aggregators; this adapter adds deterministic HTML discovery under ADR-077.

## Decision

Add a `DiceAdapter` (`source_type = "dice"`) that:

1. Recognises the URL shapes /positions/{id}, /jobs/{id}, /job/{id}, /listings/{id}, /tech-jobs/{id}.
2. Rejects board indexes plus apply/login/signin/application/about/index paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Dice public recruiting boards are covered without authenticated
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
