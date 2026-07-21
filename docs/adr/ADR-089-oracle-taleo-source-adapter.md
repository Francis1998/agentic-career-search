# ADR-089: Oracle Taleo Public Careers Source Adapter

**Date:** 2026-07-19
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Oracle Taleo (classic `*.taleo.net`) and Oracle Cloud HCM Recruiting
(`*.oraclecloud.com`) still host a large share of Fortune-500 career sites.
Popular job-search stacks (jobo.world ATS scrapers, career-ops, Greenhouse/Lever
kits) already cover Greenhouse, Lever, Ashby, Workday, and iCIMS — but Taleo
boards remain a common gap because listing pages mix query-parameter
requisitions (`jobdetail.ftl?job=XXXX`) with path-shaped `/jobs/{id}` links.

HTML URL-shape adapters (iCIMS ADR-087, Jobvite ADR-086) already proved that
deterministic href matching outperforms brittle CSS class scraping for
enterprise ATS portals.

## Decision

Add an `OracleTaleoAdapter` (`source_type = "oracle_taleo"`) that:

1. Recognises posting detail hrefs via `job=` / `jobId` / `requisitionId` query
   parameters or terminal `/job/{id}` / `/jobs/{id}` path segments.
2. Rejects apply/login terminals (`mode=apply`, trailing `apply`/`login`).
3. Falls back to the anchor `title` attribute when link text is empty.
4. Scopes location lookup to the nearest posting container.

## Consequences

- Closes the Oracle Taleo coverage gap without authenticated APIs.
- Keeps enrichment (GPT-5.5 / Claude Sonnet 4.6 / Gemini 2.5 / Kimi K2) optional
  and separate from deterministic discovery.
- Companion fix: `JsonLdAdapter._is_remote` now accepts IRI/CURIE
  `Telecommute` values via `_type_term`, matching `@type` handling.
