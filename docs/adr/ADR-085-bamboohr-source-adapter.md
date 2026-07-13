# ADR-085: BambooHR Hosted Careers JSON Source Adapter

**Date:** 2026-07-13
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

BambooHR (`{tenant}.bamboohr.com`) is a widely adopted HRIS/ATS across
small-to-mid-market employers in technology, healthcare, and professional
services. Unlike every existing adapter in this package
(greenhouse/lever/ashby/workable/recruitee/smartrecruiters/teamtailor/personio),
BambooHR does **not** render postings as anchors in the careers page HTML: the
hosted careers site (`{tenant}.bamboohr.com/careers`) is a client-rendered app
whose postings are only present after JavaScript execution. Scraping the static
markup therefore yields nothing.

BambooHR's postings are, however, exposed through a stable public JSON endpoint
at `{origin}/careers/list`, which returns:

```json
{ "result": [ { "id": 4821, "jobOpeningName": "...", "location": {...}, "isRemote": false } ] }
```

Each posting's public page is `{origin}/careers/{id}`. This is the same surface
the vendor's own careers widget consumes, so it is the practical, documented way
to enumerate a tenant's openings without a per-customer API key.

## Decision

Add a `BambooHrAdapter` (`source_type = "bamboohr"`, ADR-077 field contract
still applies) — the package's first **structured-JSON** source adapter — that
reads the public list endpoint instead of scraping HTML.

Parsing rules:

1. **Endpoint derivation** — the tenant origin (`scheme://host`) is derived from
   any supplied BambooHR careers URL, and the adapter always requests
   `{origin}/careers/list`. This means a configured `base_url` of
   `.../careers`, `.../careers/{id}`, or the bare origin all resolve correctly.
2. **Field derivation**
   - `external_id` is the opening's `id`, coerced to a trimmed string.
   - `title` is `jobOpeningName`; an empty/whitespace title is skipped.
   - `location` handles both the nested `{city, state, country}` object and a
     bare string, falling back to `Remote` when `isRemote` is `true` and no
     location is present.
   - `company` is inferred from the endpoint host.
   - `url` is `{origin}/careers/{id}`.
3. **Blank-id guard** — rows whose `id` is empty or whitespace are skipped. A
   blank id would build the bare `/careers/` URL for every such row, so URL
   deduplication would otherwise silently collapse all of them into one phantom
   posting.
4. **Deduplication** — candidates are de-duplicated by resolved URL within a
   single fetch, and `max_jobs <= 0` yields no candidates.

## Consequences

- BambooHR-hosted boards are covered via their stable JSON surface, sidestepping
  the client-rendered-HTML problem that defeats DOM scraping.
- The base adapter's HTTP helper (which returns the response body) is reused for
  the JSON fetch; only parsing differs, keeping the adapter contract uniform.
- Behavior is covered by regression tests in
  `tests/unit/test_bamboohr_adapter.py` (field extraction across object/string
  locations and remote fallback, blank-id row skipping, missing-title skipping,
  invalid-JSON error surfacing, list-endpoint derivation, zero max).
