# ADR-100: Gem Public Careers Source Adapter

**Date:** 2026-07-29
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Gem is a recruiting CRM and ATS used by growth and enterprise hiring teams. Its
public career sites are commonly hosted at `jobs.gem.com/{company}` with detail
pages at `/{company}/{jobId}`, and some tenants also expose
`{company}.gem.com/careers/...` vanity domains. Listing pages may render
postings as static anchors whose hrefs follow `/{company}/{jobId}`,
`/jobs/{jobId}`, or `/openings/{id}` shapes.

The existing HTML adapters (Freshteam, Teamtailor, Pinpoint, Comeet) already
use deterministic URL-shape matching instead of brittle CSS-only scraping. Gem
fits that pattern. A public Job Board API also exists, but this adapter stays
aligned with the HTML URL-shape contract used by sibling adapters so discovery
remains consistent across sources.

## Decision

Add a `GemAdapter` (`source_type = "gem"`) that:

1. Recognises posting detail hrefs with a `jobs.gem.com/{company}/{jobId}`
   segment pair (base64url-style tokens).
2. Accepts alternate detail prefixes `jobs/{jobId}` and `openings/{id}`.
3. Accepts `{company}.gem.com/careers/{jobId}` and
   `/careers/jobs/{jobId}` / `/careers/openings/{id}` vanity shapes.
4. Rejects the board index plus apply/login/application/about paths.
5. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
6. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Gem-hosted public boards are covered without authenticated Gem APIs or
  headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
