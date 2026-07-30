# ADR-103: Avature Public Careers Source Adapter

**Date:** 2026-07-30
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Avature is a recruiting CRM and ATS used by enterprise hiring teams. Its public
career portals commonly expose listing pages whose postings render as anchors.
Detail hrefs follow several stable shapes: modern path forms such as
`/JobDetail/{id}`, legacy ASPX query forms such as
`/JobDetail.aspx?JobId={id}`, careers vanity paths
(`/careers/{id}`, `/careers/job/{id}`, `/careers/VacancyDetail/{id}`), and
vacancy paths (`/Vacancy/{id}`, `/vacancies/{id}`).

The existing HTML adapters (Gem, Fountain, Freshteam, Teamtailor) already use
deterministic URL-shape matching instead of brittle CSS-only scraping. Avature
fits that pattern. Authenticated Avature APIs are out of scope; this adapter
stays aligned with the HTML URL-shape contract used by sibling adapters so
discovery remains consistent across sources.

## Decision

Add an `AvatureAdapter` (`source_type = "avature"`) that:

1. Recognises `/JobDetail/{id}` path postings and
   `/JobDetail.aspx?JobId={id}` query postings, preferring the path-segment id
   when both are present.
2. Accepts `/careers/{id}`, `/careers/job/{id}`, and
   `/careers/VacancyDetail/{id}` vanity shapes.
3. Accepts `/Vacancy/{id}` and `/vacancies/{id}` vacancy shapes.
4. Rejects board indexes plus apply/login/RegisterCandidate/about paths.
5. Resolves titles from anchor text first, then `title` / `aria-label` /
   `data-job-title` attributes.
6. Resolves location from `data-location` / `data-job-location`, a remote flag,
   or the shared nearest-container location helper.

## Consequences

- Avature-hosted public boards are covered without authenticated Avature APIs or
  headless browsers.
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
