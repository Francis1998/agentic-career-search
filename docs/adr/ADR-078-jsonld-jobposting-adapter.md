# ADR-078: schema.org JobPosting JSON-LD Source Adapter

**Date:** 2026-07-05
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

The Greenhouse and Lever adapters each scrape a specific vendor's HTML DOM.
Adding coverage for another board (Ashby, SmartRecruiters, Workable, a bespoke
career site, ...) has meant writing and maintaining a new DOM scraper per
vendor, each brittle against markup changes.

Modern applicant tracking systems already publish their postings as
[`schema.org/JobPosting`](https://schema.org/JobPosting) structured data inside
`<script type="application/ld+json">` blocks, because Google Jobs requires it for
indexing. That payload is a documented, stable contract shared across vendors.

## Decision

Add a vendor-neutral `JsonLdAdapter` (`source_type = "jsonld"`, ADR-077 field
contract still applies) that derives `JobCandidate` records from embedded
JobPosting JSON-LD rather than a vendor-specific DOM.

Parsing rules:

1. **Discovery** — every `<script type="application/ld+json">` block is decoded
   independently. A block that fails JSON decoding is skipped so one malformed
   payload never discards valid postings elsewhere on the page.
2. **Traversal** — JobPosting objects are collected from bare objects, arrays,
   `@graph` containers, and `ItemList` wrappers by descending into
   non-JobPosting containers. `@type` may be a string or a list containing
   `"JobPosting"`.
3. **Field derivation**
   - `title` is required; an object without a non-empty string title is skipped.
   - `external_id` comes from `identifier` (a string, or a `PropertyValue`
     `value`).
   - `company` comes from `hiringOrganization` (a string or an `Organization`
     `name`), falling back to the URL host.
   - `location` is the first resolvable `jobLocation` `Place` rendered as
     `Locality, Region, Country`; a `jobLocationType` of `TELECOMMUTE` with no
     address resolves to `Remote`.
   - `url` is resolved against the source URL, falling back to the source URL.
4. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- One adapter covers any board that publishes JobPosting structured data,
  reducing per-vendor scraper maintenance.
- Behavior is covered by regression tests in
  `tests/unit/test_jsonld_adapter.py` (single posting, `@graph`, remote roles,
  malformed-block skipping, URL dedup, zero max).
- Boards that do not emit JSON-LD are still served by the dedicated
  Greenhouse/Lever adapters.
