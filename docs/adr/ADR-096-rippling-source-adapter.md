# ADR-096: Rippling Public Careers Source Adapter

**Date:** 2026-07-27
**Status:** Accepted
**Context:** Job Search Automation - public board adapters

## Context

Rippling publishes public job boards and posting detail pages on Rippling-owned
domains, most commonly `ats.rippling.com/{company}/jobs` with individual roles
at `/{company}/jobs/{uuid}`. Search results and public examples show posting
detail URLs with UUID identifiers and optional tracking query parameters such as
`jobSite=LinkedIn`.

The existing BreezyHR and Freshteam adapters use deterministic HTML URL-shape
matching instead of brittle CSS-only scraping. Rippling fits that pattern: the
stable part of the public surface is the terminal `/jobs/{uuid}` detail path,
not any specific class name.

## Decision

Add a `RipplingAdapter` (`source_type = "rippling"`) that derives
`JobCandidate` records from public posting anchors.

Parsing rules:

1. **Discovery** - every `<a href>` on the page is inspected. An anchor is a
   posting only when its path contains a `jobs` segment immediately followed by
   a UUID segment and that UUID is the terminal path segment. Absolute URLs must
   be on `rippling.com` or one of its subdomains; relative links are accepted so
   branded boards can resolve against their configured base URL.
2. **Rejection** - the board index (`/jobs`), deeper application paths
   (`/jobs/{uuid}/apply`), generic careers navigation, and absolute external
   domains are not candidates.
3. **Field derivation**
   - `title` is the anchor's text, falling back to `title`, `aria-label`, and
     `data-title` attributes for icon-only anchors.
   - `external_id` is the UUID captured from the terminal detail URL.
   - `company` is inferred from the configured URL host.
   - `location` is resolved within the anchor's nearest posting container
     (a `class` matching `job`/`position`/`posting`/`opening`/`role`).
   - `url` is resolved against the source URL.
4. **Deduplication and bounds** - candidates are de-duplicated by resolved URL,
   and `max_jobs <= 0` yields no candidates.

## Consequences

- Rippling-hosted public boards (`*.rippling.com`, especially
  `ats.rippling.com`) are covered without authenticated APIs or headless
  browsers.
- Conservative UUID matching avoids treating board navigation, application
  steps, or unrelated external job links as candidates.
- Behavior is covered by regression tests in
  `tests/unit/test_rippling_adapter.py` (field extraction, non-posting link
  rejection, zero max, title fallback, and per-posting location scoping).
- Deterministic discovery remains separate from optional enrichment by GPT-5.5 /
  Claude Sonnet 4.6 / Gemini 3.x / Kimi K2.
