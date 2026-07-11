# ADR-084: Personio Public Careers Site Source Adapter

**Date:** 2026-07-11
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Personio (`{tenant}.jobs.personio.de` / `{tenant}.jobs.personio.com`) is the
dominant applicant tracking system across DACH and wider EU small-to-mid-market
employers. Its public careers site is server-rendered and exposes every posting
as an anchor whose href follows a stable `/job/{jobId}` shape, where `jobId` is
the posting's canonical numeric identifier (e.g. `58291`) and an optional
lowercase, hyphenated title slug may trail the id (`/job/2623782-marketing-manager`).
Crucially the path segment is the *singular* `job`, which distinguishes Personio
posting URLs from Teamtailor's plural `/jobs/{jobId}-{slug}` shape (ADR-083).

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but Personio careers sites do not reliably ship
that payload in their server-rendered HTML. A dedicated adapter that keys on the
posting URL shape provides deterministic coverage without depending on
structured data being present, mirroring the `WorkableAdapter` (ADR-080),
`AshbyAdapter` (ADR-079), `RecruiteeAdapter` (ADR-081),
`SmartRecruitersAdapter` (ADR-082), and `TeamtailorAdapter` (ADR-083).

## Decision

Add a `PersonioAdapter` (`source_type = "personio"`, ADR-077 field contract
still applies) that derives `JobCandidate` records from posting anchors.

Parsing rules:

1. **Discovery** — every `<a href>` on the page is inspected. An anchor is a
   posting only when its path contains a singular `job` segment immediately
   followed by a segment matching `^(\d+)(?:-[a-z0-9-]+)?$` (a numeric job id,
   optionally followed by a hyphenated title slug) **and** that id segment is
   the terminal path segment. Requiring the id to be terminal deterministically
   excludes the application step (`/job/{jobId}/apply`), whose numeric id
   segment is not terminal, as well as the plural `/jobs` list page and
   navigation/external links regardless of their CSS classes.
2. **Field derivation**
   - `title` is the anchor's text (joined with spaces so nested inline markup
     does not collapse adjacent words); an empty title is skipped.
   - `external_id` is the numeric `jobId` captured from the matching segment.
   - `company` is inferred from the URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `job`/`position`/`posting`), so a posting without its
     own location does not inherit a sibling's location.
   - `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- Personio careers sites (both `*.jobs.personio.de` and `*.jobs.personio.com`
  tenants) are covered deterministically by URL shape rather than depending on
  the presence of JSON-LD structured data.
- Behavior is covered by regression tests in
  `tests/unit/test_personio_adapter.py` (field extraction, non-posting and
  application-step link rejection, `.de`/`.com` domain support, per-posting
  location scoping, zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
