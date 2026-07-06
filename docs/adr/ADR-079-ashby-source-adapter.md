# ADR-079: Ashby Public Job Board Source Adapter

**Date:** 2026-07-06
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Ashby (`jobs.ashbyhq.com/{org}`) is a widely adopted modern applicant tracking
system, especially among high-growth startups. Its public board is a
single-page application, but every posting is exposed as an anchor whose href
follows a stable `/{org}/{uuid}` shape, where `uuid` is the posting's canonical
identifier.

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but Ashby boards do not reliably ship that
payload in their server-rendered HTML. A dedicated adapter that keys on the
posting URL shape provides deterministic coverage without depending on
structured data being present.

## Decision

Add an `AshbyAdapter` (`source_type = "ashby"`, ADR-077 field contract still
applies) that derives `JobCandidate` records from posting anchors.

Parsing rules:

1. **Discovery** — every `<a href>` on the page is inspected. An anchor is a
   posting only when its URL's final path segment is a UUID
   (`8-4-4-4-12` hex). This deterministically excludes navigation, application,
   and external legal links regardless of their CSS classes.
2. **Field derivation**
   - `title` is the anchor's text (joined with spaces so nested inline markup
     does not collapse adjacent words); an empty title is skipped.
   - `external_id` is the trailing UUID path segment.
   - `company` is inferred from the URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `posting`/`job`), so a posting without its own
     location does not inherit a sibling's location.
   - `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- Ashby boards are covered deterministically by URL shape rather than depending
  on the presence of JSON-LD structured data.
- Behavior is covered by regression tests in `tests/unit/test_adapters.py`
  (field extraction, non-posting link rejection, per-posting location scoping,
  zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
