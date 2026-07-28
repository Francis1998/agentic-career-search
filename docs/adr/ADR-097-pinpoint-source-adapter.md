# ADR-097: Pinpoint HR Public Careers Source Adapter

**Date:** 2026-07-28
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Pinpoint is a popular ATS for mid-market and growth-stage employers. Its public
career sites are usually hosted at `{org}.pinpointhq.com`. Listing pages expose
postings as static anchors whose hrefs follow `/postings/{uuid}` (optionally
locale-prefixed, for example `/en/postings/{uuid}`) or the older
`/jobs/{jobId}` shape.

The existing HTML adapters (Freshteam, Teamtailor, Jobvite, BreezyHR) already
use deterministic URL-shape matching instead of brittle CSS-only scraping.
Pinpoint fits that pattern. A public `postings.json` feed also exists, but this
adapter stays aligned with the HTML URL-shape contract used by sibling adapters
so discovery remains consistent across sources.

## Decision

Add a `PinpointAdapter` (`source_type = "pinpoint"`) that:

1. Recognises posting detail hrefs with a `postings/{uuid}` segment pair
   (UUID v4-style tokens) or `jobs/{jobId}` with an optional title slug.
2. Accepts an optional leading locale segment (`en`, `en-gb`, …) before
   `postings` / `jobs`.
3. Rejects the board index plus apply/login/application paths.
4. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
5. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Pinpoint-hosted public boards are covered without authenticated Pinpoint APIs
  or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
