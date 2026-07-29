# ADR-099: Fountain Public Careers Source Adapter

**Date:** 2026-07-29
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Fountain is a popular high-volume hiring platform for hourly and frontline
workforces. Its public career sites are commonly hosted at `{org}.fountain.com`
or `web.fountain.com`. Listing pages expose postings as static anchors whose
hrefs follow `/apply/{company}/{positionId}`, tenant `/apply/{slug}` shapes, or
`/jobs/{jobId}`, `/openings/{id}`, and `/positions/{id}` paths.

The existing HTML adapters (Freshteam, Teamtailor, Jobvite, BreezyHR, Pinpoint)
already use deterministic URL-shape matching instead of brittle CSS-only scraping.
Fountain fits that pattern. Fountain also exposes APIs, but this adapter stays
aligned with the HTML URL-shape contract used by sibling adapters so discovery
remains consistent across sources.

## Decision

Add a `FountainAdapter` (`source_type = "fountain"`) that:

1. Recognises posting detail hrefs with `/apply/{company}/{positionId}` on
   `web.fountain.com`, `/apply/{slug}` on tenant subdomains, and
   `/jobs/{jobId}`, `/openings/{id}`, or `/positions/{id}` detail paths.
2. Rejects board index pages, apply confirmation/login steps, and about links.
3. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
4. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Fountain-hosted public boards are covered without authenticated Fountain APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
