# ADR-077: Source Adapter Parsing Contract

**Date:** 2026-07-03
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

The Greenhouse and Lever adapters parse loosely structured public HTML into
`JobCandidate` records. Two subtle parsing defects showed that the adapters
lacked an explicit contract for two derived fields:

- **`external_id`** — Greenhouse previously concatenated *any* digits found in
  the trailing path segment, so a title slug such as `senior-engineer-2024`
  produced `2024` (a calendar year) as the job id.
- **`location`** — Greenhouse resolved the location via
  `anchor.find_next("span", class_="location")`, which scans the whole document
  forward. An opening that lacked its own location span therefore inherited the
  location of the *next* posting on the page.

Both defects silently corrupt candidate metadata that downstream scoring,
deduplication, and persistence rely on.

## Decision

Adapters MUST honor the following field-derivation contract:

1. **`external_id` is only assigned from an unambiguous identifier.**
   - Greenhouse: a `gh_jid`/`jid` query parameter, or a trailing path segment
     that is *entirely* numeric (`str.isdigit()`). Otherwise `external_id` is
     `None`. Embedded digits inside a slug are never treated as an id.
   - Lever: the trailing path segment (opaque slug/uuid).

2. **`location` is resolved only within the posting's own container.**
   Location lookup is scoped to the anchor's parent `div.opening`
   (Greenhouse) or `div.posting` (Lever). Cross-posting document-order scans are
   prohibited, so a posting without its own location resolves to `None` rather
   than borrowing a sibling's.

## Consequences

- A missing `external_id` or `location` is represented as `None`, never as a
  best-guess value scraped from unrelated markup. Consumers must treat these
  fields as optional (they already are on `JobCandidate`).
- Each adapter field-derivation rule is covered by a regression test
  (`tests/unit/test_adapters.py`) proven to fail against the previous behavior.
- New source adapters added under `src/autoapply_agent/adapters/` MUST follow
  this contract for any identifier or location they derive.
