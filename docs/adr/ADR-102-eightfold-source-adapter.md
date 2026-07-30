# ADR-102: Eightfold AI Public Careers Source Adapter

**Date:** 2026-07-30
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Eightfold AI is a talent-intelligence platform used by enterprise hiring teams.
Its public career sites are commonly hosted at `{company}.eightfold.ai` with
listing pages under `/careers` and detail pages at `/careers/job/{id}` (optional
slug), `/career_detail/{id}`, `/position/{id}`, or `/jobs/{id}`. Listing pages
render postings as static anchors alongside board-index, apply/login, and search
facet links that must not become candidates.

The existing HTML adapters (Gem, Freshteam, Teamtailor, Pinpoint, Comeet) already
use deterministic URL-shape matching instead of brittle CSS-only scraping.
Eightfold fits that pattern. Authenticated Talent Acquisition APIs exist, but
this adapter stays aligned with the HTML URL-shape contract used by sibling
adapters so discovery remains consistent across sources.

## Decision

Add an `EightfoldAdapter` (`source_type = "eightfold"`) that:

1. Recognises posting detail hrefs shaped as `/careers/job/{id}` and
   `/careers/job/{id}/{slug}`.
2. Accepts alternate detail prefixes `/career_detail/{id}`, `/position/{id}`,
   and `/jobs/{id}`.
3. Rejects the board index `/careers`, apply/login/signin/about paths, and
   search/facet navigation.
4. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
5. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Eightfold-hosted public boards are covered without authenticated Eightfold
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
