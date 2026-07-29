# ADR-098: Comeet Public Careers Source Adapter

**Date:** 2026-07-29
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Comeet is a popular ATS for growth-stage and enterprise employers, similar to
Lever, Ashby, and Pinpoint. Its public career sites are commonly hosted at
`www.comeet.co` or `www.comeet.com`. Listing pages expose postings as static
anchors whose hrefs follow
`/jobs/{company}/{companyId}/{jobSlug}/{jobId}`.

The existing HTML adapters (Freshteam, Teamtailor, Jobvite, BreezyHR, Pinpoint)
already use deterministic URL-shape matching instead of brittle CSS-only scraping.
Comeet fits that pattern. A public API also exists, but this adapter stays
aligned with the HTML URL-shape contract used by sibling adapters so discovery
remains consistent across sources.

## Decision

Add a `ComeetAdapter` (`source_type = "comeet"`) that:

1. Recognises posting detail hrefs with a
   `jobs/{company}/{companyId}/{jobSlug}/{jobId}` segment chain.
2. Rejects the board index (`/jobs/{company}/{companyId}`) plus apply/login/about
   paths.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Comeet-hosted public boards are covered without authenticated Comeet APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
