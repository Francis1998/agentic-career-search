# ADR-083: Teamtailor Public Careers Site Source Adapter

**Date:** 2026-07-10
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Teamtailor (`{company}.teamtailor.com`) is a widely adopted applicant tracking
system, especially across European employers. Its public careers site is a
single-page application, but every posting is exposed as an anchor whose href
follows a stable `/jobs/{jobId}-{slug}` shape, where `jobId` is the posting's
canonical numeric identifier (e.g. `3681317`) and `slug` is an optional
lowercase, hyphenated title token. Customers who host the career site on a
custom domain reuse the same tail under a `/careers` prefix
(`example.com/careers/jobs/{jobId}-{slug}`).

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but Teamtailor careers sites do not reliably
ship that payload in their server-rendered HTML. A dedicated adapter that keys
on the posting URL shape provides deterministic coverage without depending on
structured data being present, mirroring the `WorkableAdapter` (ADR-080),
`AshbyAdapter` (ADR-079), `RecruiteeAdapter` (ADR-081), and
`SmartRecruitersAdapter` (ADR-082).

## Decision

Add a `TeamtailorAdapter` (`source_type = "teamtailor"`, ADR-077 field contract
still applies) that derives `JobCandidate` records from posting anchors.

Parsing rules:

1. **Discovery** — every `<a href>` on the page is inspected. An anchor is a
   posting only when its path contains a `jobs` segment immediately followed by
   a segment matching `^(\d+)(?:-[a-z0-9-]+)?$` (a numeric job id, optionally
   followed by a hyphenated title slug) **and** that id segment is the terminal
   path segment. Requiring the id to be terminal deterministically excludes the
   jobs list page (`/jobs`) and the application form
   (`/jobs/{jobId}/applications/new`), whose numeric id segment is not terminal,
   as well as navigation and external links regardless of their CSS classes.
2. **Field derivation**
   - `title` is the anchor's text (joined with spaces so nested inline markup
     does not collapse adjacent words); an empty title is skipped.
   - `external_id` is the numeric `jobId` captured from the matching segment.
   - `company` is inferred from the URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `job`/`posting`/`opening`), so a posting without its
     own location does not inherit a sibling's location.
   - `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- Teamtailor careers sites (both `*.teamtailor.com` and custom-domain
  `/careers/jobs/...` deployments) are covered deterministically by URL shape
  rather than depending on the presence of JSON-LD structured data.
- Behavior is covered by regression tests in
  `tests/unit/test_teamtailor_adapter.py` (field extraction, non-posting and
  application-form link rejection, custom-domain prefix support, per-posting
  location scoping, zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
