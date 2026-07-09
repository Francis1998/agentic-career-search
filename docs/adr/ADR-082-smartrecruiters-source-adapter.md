# ADR-082: SmartRecruiters Public Careers Site Source Adapter

**Date:** 2026-07-09
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

SmartRecruiters (`jobs.smartrecruiters.com/{company}`) is a widely adopted
enterprise applicant tracking system. Its public careers site is a single-page
application, but every posting is exposed as an anchor whose href follows a
stable `/{company}/{jobId}-{slug}` shape, where `jobId` is the posting's
canonical numeric identifier (a long digit string, e.g. `744000123456789`) and
`slug` is an optional lowercase, hyphenated title token.

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but SmartRecruiters careers sites do not
reliably ship that payload in their server-rendered HTML. A dedicated adapter
that keys on the posting URL shape provides deterministic coverage without
depending on structured data being present, mirroring the `WorkableAdapter`
(ADR-080), `AshbyAdapter` (ADR-079), and `RecruiteeAdapter` (ADR-081).

## Decision

Add a `SmartRecruitersAdapter` (`source_type = "smartrecruiters"`, ADR-077 field
contract still applies) that derives `JobCandidate` records from posting
anchors.

Parsing rules:

1. **Discovery** — every `<a href>` on the page is inspected. An anchor is a
   posting only when one of its path segments matches `^(\d{6,})(?:-[a-z0-9-]+)?$`
   (a numeric job id, optionally followed by a hyphenated title slug). This
   deterministically excludes navigation, search, and external legal links
   regardless of their CSS classes.
2. **Field derivation**
   - `title` is the anchor's text (joined with spaces so nested inline markup
     does not collapse adjacent words); an empty title is skipped.
   - `external_id` is the numeric `jobId` prefix of the matching segment.
   - `company` is inferred from the URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `opening`/`job`/`posting`), so a posting without its own
     location does not inherit a sibling's location.
   - `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- SmartRecruiters careers sites are covered deterministically by URL shape
  rather than depending on the presence of JSON-LD structured data.
- Behavior is covered by regression tests in `tests/unit/test_adapters.py`
  (field extraction, non-posting link rejection, per-posting location scoping,
  zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
