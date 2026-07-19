# ADR-091: Phenom Public Careers Source Adapter

**Date:** 2026-07-19
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Phenom (`*.phenompeople.com` and vanity-domain careers experiences) powers a
large share of enterprise career sites. Popular job-search stacks already cover
Greenhouse, Lever, Ashby, Workday, iCIMS, Taleo, and SuccessFactors — but Phenom
boards remain a common gap because listing pages use locale-prefixed
`/job/{id}/{slug}` URL shapes that generic CSS scrapers miss.

HTML URL-shape adapters (iCIMS ADR-087, Jobvite ADR-086, Taleo ADR-089,
SuccessFactors ADR-090) already proved that deterministic href matching
outperforms brittle CSS class scraping for enterprise ATS portals.

## Decision

Add a `PhenomAdapter` (`source_type = "phenom"`) that:

1. Recognises posting detail hrefs via terminal `/job/{id}` / `/jobs/{id}` path
   segments (optional slug; locale prefixes such as `/us/en/` allowed) or
   `jobId` / `job_id` query parameters.
2. Rejects apply/login terminals and `/jobs/search` listing grids.
3. Falls back to the anchor `title` attribute when link text is empty.
4. Scopes location lookup to the nearest posting container.

## Consequences

- Closes the Phenom coverage gap without authenticated APIs.
- Keeps enrichment (GPT-5.5 / Claude Sonnet 4.6 / Gemini 2.5 / Kimi K2) optional
  and separate from deterministic discovery.
- Companion fix: `WorkdayAdapter` CXS `Referer` now uses the board's parsed
  locale instead of a hardcoded `en-US`, so non-US boards (e.g. `fr-FR`,
  `de-DE`) send a matching Referer.
