# ADR-090: SAP SuccessFactors Public Careers Source Adapter

**Date:** 2026-07-19
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

SAP SuccessFactors (`*.successfactors.com` / `*.successfactors.eu`) hosts a
large share of Fortune-500 career sites. Popular job-search stacks (jobo.world
ATS scrapers, career-ops, Greenhouse/Lever kits) already cover Greenhouse,
Lever, Ashby, Workday, iCIMS, and Taleo — but SuccessFactors boards remain a
common gap because listing pages mix query-parameter requisitions
(`jobreqcareer?jobId=XXXX`, `career_job_req_id=XXXX`) with path-shaped
`/jobs/{id}` links.

HTML URL-shape adapters (iCIMS ADR-087, Jobvite ADR-086, Taleo ADR-089) already
proved that deterministic href matching outperforms brittle CSS class scraping
for enterprise ATS portals.

## Decision

Add a `SuccessFactorsAdapter` (`source_type = "successfactors"`) that:

1. Recognises posting detail hrefs via `jobId` / `career_job_req_id` /
   `job_req_id` / `job` query parameters or terminal `/job/{id}` / `/jobs/{id}`
   path segments.
2. Rejects apply/login terminals (`mode=apply`, trailing `apply`/`login`).
3. Falls back to the anchor `title` attribute when link text is empty.
4. Scopes location lookup to the nearest posting container.

## Consequences

- Closes the SAP SuccessFactors coverage gap without authenticated APIs.
- Keeps enrichment (GPT-5.5 / Claude Sonnet 4.6 / Gemini 2.5 / Kimi K2) optional
  and separate from deterministic discovery.
- Companion fix: `JobviteAdapter` now falls back to the anchor `title`
  attribute when visible text is empty (mirroring iCIMS), so icon-only Jobvite
  listing links survive.
