# ADR-080: Workable Public Job Board Source Adapter

**Date:** 2026-07-07
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Workable (`apply.workable.com/{company}`) is a widely adopted applicant tracking
system, especially among small and mid-sized companies. Its public board is a
single-page application, but every posting is exposed as an anchor whose href
follows a stable `/{company}/j/{shortcode}` shape, where `shortcode` is the
posting's canonical uppercase alphanumeric identifier.

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but Workable boards do not reliably ship that
payload in their server-rendered HTML. A dedicated adapter that keys on the
posting URL shape provides deterministic coverage without depending on
structured data being present, mirroring the `AshbyAdapter` (ADR-079).

## Decision

Add a `WorkableAdapter` (`source_type = "workable"`, ADR-077 field contract
still applies) that derives `JobCandidate` records from posting anchors.

Parsing rules:

1. **Discovery** — every `<a href>` on the page is inspected. An anchor is a
   posting only when its path contains a `/j/{shortcode}` segment pair, where
   `shortcode` matches `^[0-9A-Z]{6,}$`. This deterministically excludes
   navigation, department, and external legal links regardless of their CSS
   classes.
2. **Field derivation**
   - `title` is the anchor's text (joined with spaces so nested inline markup
     does not collapse adjacent words); an empty title is skipped.
   - `external_id` is the `/j/` shortcode segment.
   - `company` is inferred from the URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `posting`/`job`/`opening`), so a posting without its
     own location does not inherit a sibling's location.
   - `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- Workable boards are covered deterministically by URL shape rather than
  depending on the presence of JSON-LD structured data.
- Behavior is covered by regression tests in `tests/unit/test_adapters.py`
  (field extraction, non-posting link rejection, per-posting location scoping,
  zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
