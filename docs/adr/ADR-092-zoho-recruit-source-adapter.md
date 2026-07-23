# ADR-092: Zoho Recruit Public Careers Source Adapter

**Date:** 2026-07-23
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Zoho Recruit public careers boards (`*.zohorecruit.com`, plus vanity-domain
proxies) are common on SMB and mid-market hiring sites. Popular job-search
stacks already cover Greenhouse, Lever, Ashby, Workday, iCIMS, Taleo, and
SuccessFactors — but Zoho Recruit boards remain a coverage gap because listing
pages mix query-parameter ids (`jobId=XXXX`, `jid=XXXX`, `job_id=XXXX`) with
several path-shaped posting detail links.

HTML URL-shape adapters (iCIMS ADR-087, Jobvite ADR-086, Taleo ADR-089,
SuccessFactors ADR-090) already proved that deterministic href matching
outperforms brittle CSS class scraping for ATS portals.

## Decision

Add a `ZohoRecruitAdapter` (`source_type = "zoho_recruit"`) that:

1. Recognises posting detail hrefs via `jobId` / `jid` / `job_id` query
   parameters or terminal `/job/{id}` / `/jobs/{id}` / `/careers/{id}` /
   `/Jobs/Careers/{id}` path segments.
2. Rejects apply/login terminals (`mode=apply`, `source=apply`, trailing
   `apply`/`login`).
3. Falls back to the anchor `title` attribute when link text is empty.
4. Scopes location lookup to the nearest posting container.

## Consequences

- Closes the Zoho Recruit coverage gap without authenticated APIs.
- Keeps enrichment (GPT-5.5 / Claude Sonnet 4.6 / Gemini 2.5 / Kimi K2)
  optional and separate from deterministic discovery.
- Regression coverage ensures Zoho `source=apply` apply links are rejected, the
  same way SuccessFactors rejects `mode=apply` apply links.
