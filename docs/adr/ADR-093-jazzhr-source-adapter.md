# ADR-093: JazzHR Public Careers Source Adapter

**Date:** 2026-07-25
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

JazzHR public careers boards (`{tenant}.applytojob.com/apply`, plus
vanity-domain proxies) are common on SMB and mid-market hiring sites. Popular
job-search stacks already cover Greenhouse, Lever, Ashby, Workday, iCIMS,
Taleo, SuccessFactors, and Zoho Recruit — but JazzHR boards remain a coverage
gap because listing pages expose postings as apply-path links rather than a
single stable CSS class.

HTML URL-shape adapters (iCIMS ADR-087, Jobvite ADR-086, Taleo ADR-089,
SuccessFactors ADR-090, Zoho Recruit ADR-092) already proved that deterministic
href matching outperforms brittle CSS class scraping for ATS portals.

## Decision

Add a `JazzHrAdapter` (`source_type = "jazzhr"`) that:

1. Recognises posting detail hrefs via `/apply/{jobId}` and
   `/apply/{jobId}/{slug}` path shapes.
2. Rejects apply-root, search, legacy jobs, and deeper application-step links.
3. Falls back to the anchor `title` attribute when link text is empty.
4. Scopes location lookup to the nearest posting container.

## Consequences

- Closes the JazzHR coverage gap without authenticated APIs.
- Keeps enrichment (GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2)
  optional and separate from deterministic discovery.
- Regression coverage ensures JazzHR listing navigation is rejected while both
  supported posting URL shapes are accepted.
