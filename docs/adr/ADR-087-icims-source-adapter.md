# ADR-087: iCIMS Public Careers Portal Source Adapter

**Date:** 2026-07-15
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

iCIMS is one of the most widely deployed enterprise applicant tracking systems.
Its public careers portals are hosted at `careers-{tenant}.icims.com` (with the
`careers.{tenant}.icims.com` variant and vanity-domain proxies such as
`jobs.{company}.com` that front the same portal). Each posting detail page
follows a stable `/jobs/{jobId}/{slug}/job` shape, where `jobId` is a numeric
requisition id and the `{slug}` segment is optional (`/jobs/{jobId}/job`). The
distinguishing feature is the *terminal literal* `job` segment: it separates a
posting detail page from the `/jobs/search` listing grid and from the
application step (`?mode=apply` / a terminal `login` segment).

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, and iCIMS static posting pages often do carry a
JobPosting block; however, the portal listing pages are client-rendered and do
not reliably surface JSON-LD for the whole board, so a URL-shape adapter gives
deterministic discovery from the listing grid. This mirrors the existing
greenhouse/lever/ashby/workable/recruitee/smartrecruiters/teamtailor/personio/
jobvite adapters. Jobvite (ADR-086) also uses a `/job/{id}` singular shape, but
its ids are alphanumeric and the id is terminal; iCIMS ids are purely numeric
and the terminal segment is the literal `job`, so a dedicated matcher is used.

## Decision

Add an `IcimsAdapter` (`source_type = "icims"`, ADR-077 field contract still
applies) that derives `JobCandidate` records from posting anchors.

Parsing rules:

1. **Discovery** — every `<a href>` is inspected. An anchor is a posting only
   when its path has a numeric `{jobId}` segment immediately following a `jobs`
   segment **and** a terminal literal `job` segment
   (`/jobs/{jobId}/{slug}/job` or `/jobs/{jobId}/job`). Requiring the terminal
   `job` deterministically excludes the `/jobs/search` grid and the application
   step, whose terminal segment is not `job`.
2. **Field derivation** — `title` is the anchor text, falling back to the
   anchor's `title` attribute when the visible text is empty (icon-only /
   aria-labelled links); `external_id` is the numeric `jobId`; `company` is
   inferred from the host; `location` is resolved within the anchor's nearest
   posting container (a `class` matching `job`/`position`/`posting`) so a posting
   without its own location does not inherit a sibling's; `url` is resolved
   against the source URL (so vanity-domain hosts are preserved).
3. **Deduplication** — candidates are de-duplicated by resolved URL, and
   `max_jobs <= 0` yields no candidates.

## Consequences

- iCIMS careers portals (including vanity-domain proxies) are covered
  deterministically by URL shape rather than depending on JSON-LD being present
  on the listing grid.
- Behavior is covered by regression tests in
  `tests/unit/test_icims_adapter.py` (field extraction across the slugged and
  slug-less variants, `title`-attribute fallback, search/apply/nav rejection,
  vanity-domain recognition, per-posting location scoping, zero max).
- Boards that do emit JSON-LD on their detail pages remain served by the
  vendor-neutral `JsonLdAdapter`.
