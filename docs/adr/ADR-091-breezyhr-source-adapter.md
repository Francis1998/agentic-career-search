# ADR-091: Breezy HR Public Careers Site Source Adapter

**Date:** 2026-07-20
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Breezy HR (`{company}.breezy.hr`) is a widely adopted applicant tracking system
for startups and SMBs. Its public careers site exposes each position as an
anchor whose href follows a stable `/p/{positionId}` shape, where `positionId`
is the posting's canonical alphanumeric identifier (commonly a 12-character hex
token) and an optional hyphenated title slug may trail the id.

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but Breezy careers listing pages do not
reliably ship that payload in their server-rendered HTML. A dedicated adapter
that keys on the posting URL shape provides deterministic coverage without
depending on structured data being present, mirroring the `TeamtailorAdapter`
(ADR-083), `PersonioAdapter` (ADR-084), and `JobviteAdapter` (ADR-086).

## Decision

Add a `BreezyHrAdapter` (`source_type = "breezyhr"`, ADR-077 field contract
still applies) that derives `JobCandidate` records from posting anchors.

Parsing rules:

1. **Discovery** — every `<a href>` on the page is inspected. An anchor is a
   posting only when its path contains a `p` segment immediately followed by a
   segment matching `^([A-Za-z0-9]{6,})(?:-[A-Za-z0-9-]+)?$` **and** that id
   segment is the terminal path segment. Requiring the id to be terminal
   deterministically excludes the application step (`/p/{positionId}/apply`)
   and board navigation links regardless of their CSS classes.
2. **Field derivation**
   - `title` is the anchor's text, falling back to the `title` attribute when
     the anchor is icon-only (mirrors iCIMS/Jobvite).
   - `external_id` is the `positionId` captured from the matching segment.
   - `company` is inferred from the URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `position`/`job`/`posting`/`opening`).
   - `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- Breezy HR careers sites (`*.breezy.hr`) are covered deterministically by URL
  shape rather than depending on the presence of JSON-LD structured data.
- Behavior is covered by regression tests in
  `tests/unit/test_breezyhr_adapter.py` (field extraction, non-posting and
  application-step link rejection, title-attribute fallback, per-posting
  location scoping, zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
