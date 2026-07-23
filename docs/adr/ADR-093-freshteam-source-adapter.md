# ADR-093: Freshteam Public Careers Source Adapter

**Date:** 2026-07-22
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Freshteam, from Freshworks, is a popular ATS for SMB and mid-market employers.
Its public career sites are usually hosted at `{tenant}.freshteam.com/jobs`.
Listing pages expose postings as static anchors whose hrefs follow
`/jobs/{jobId}/{slug}`. The job id is a mixed-case token and can contain `-` or
`_`, so numeric-only matchers used by some other adapters are too restrictive.

The existing HTML adapters (Teamtailor, Jobvite, Oracle Taleo, and BreezyHR on a
parallel branch) already use deterministic URL-shape matching instead of brittle
CSS-only scraping. Freshteam fits that pattern.

## Decision

Add a `FreshteamAdapter` (`source_type = "freshteam"`) that:

1. Recognises posting detail hrefs with a `jobs/{jobId}` segment pair and an
   optional terminal title slug.
2. Accepts mixed-case alphanumeric ids with `-` / `_` characters.
3. Rejects the board index plus apply/login/application paths.
4. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-portal-title` attributes.
5. Resolves location from Freshteam `data-portal-location`, remote flags, or the
   shared nearest-container location helper.

## Consequences

- Freshteam-hosted public boards are covered without authenticated Freshworks
  APIs or headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 2.5 / Kimi K2.
- Companion fix: `TeamtailorAdapter` now accepts mixed-case title slugs because
  its numeric job id is the stable identity and slug casing is presentation text.
  A regression test covers the previously dropped mixed-case URL.
