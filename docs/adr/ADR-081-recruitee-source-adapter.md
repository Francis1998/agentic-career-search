# ADR-081: Recruitee Public Careers Site Source Adapter

**Date:** 2026-07-08
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Recruitee (`{company}.recruitee.com`) is a widely adopted applicant tracking
system, especially among European small and mid-sized companies. Its public
careers site is a single-page application, but every offer is exposed as an
anchor whose href follows a stable `/o/{slug}` shape, where `slug` is the
offer's canonical human-readable identifier (a lowercase, hyphenated token).

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but Recruitee careers sites do not reliably
ship that payload in their server-rendered HTML. A dedicated adapter that keys
on the offer URL shape provides deterministic coverage without depending on
structured data being present, mirroring the `WorkableAdapter` (ADR-080) and
`AshbyAdapter` (ADR-079).

## Decision

Add a `RecruiteeAdapter` (`source_type = "recruitee"`, ADR-077 field contract
still applies) that derives `JobCandidate` records from offer anchors.

Parsing rules:

1. **Discovery** — every `<a href>` on the page is inspected. An anchor is a
   posting only when its path contains an `/o/{slug}` segment pair, where
   `slug` matches `^[a-z0-9][a-z0-9-]*$`. This deterministically excludes
   navigation, team, and external legal links regardless of their CSS classes.
2. **Field derivation**
   - `title` is the anchor's text (joined with spaces so nested inline markup
     does not collapse adjacent words); an empty title is skipped.
   - `external_id` is the `/o/` slug segment.
   - `company` is inferred from the URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `offer`/`job`/`opening`), so a posting without its own
     location does not inherit a sibling's location.
   - `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- Recruitee careers sites are covered deterministically by URL shape rather
  than depending on the presence of JSON-LD structured data.
- Behavior is covered by regression tests in `tests/unit/test_adapters.py`
  (field extraction, non-posting link rejection, per-posting location scoping,
  zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
