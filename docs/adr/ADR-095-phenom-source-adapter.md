# ADR-095: Phenom People Public Careers Source Adapter

**Date:** 2026-07-26
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Phenom People powers many enterprise and branded careers sites. Public listing
pages commonly link postings through detail paths such as `/job/{jobId}/{slug}`
or `/jobs/{jobId}`. Those pages also include nearby list, index, login, and
application-step links that should not become job candidates.

The existing URL-shape adapters for JazzHR, Breezy HR, SuccessFactors, Taleo,
and Zoho Recruit show that deterministic href matching is more robust than
depending on tenant-specific classes. The generic JSON-LD adapter remains useful
when boards emit `schema.org/JobPosting`, but Phenom boards do not consistently
include complete structured data in the server HTML.

## Decision

Add a `PhenomPeopleAdapter` (`source_type = "phenom"`) that derives
`JobCandidate` records from posting anchors.

Parsing rules:

1. Inspect every `<a href>` on the page.
2. Accept only Phenom detail shapes:
   - `/job/{jobId}/{slug}` (locale or branded-site prefixes allowed)
   - `/jobs/{jobId}` (locale or branded-site prefixes allowed)
3. Reject list/index/search/login/application links, including explicit apply
   path segments and `action` / `mode` / `source` / `step` query values set to
   apply-style flows.
4. Derive fields under the ADR-077 adapter contract:
   - `title` from anchor text, falling back to `title`.
   - `external_id` from the captured `{jobId}` path segment.
   - `location` from the nearest posting container.
   - `company` from the source URL host.
5. Deduplicate by resolved posting URL and stop at `max_jobs`.

## Consequences

- Phenom-hosted careers sites gain deterministic coverage without authenticated
  APIs.
- Enrichment with GPT-5.5, Claude Sonnet 4.6, Gemini 3.x, or Kimi K2 remains
  optional and separate from discovery.
- Regression tests in `tests/unit/test_phenom_adapter.py` prove accepted posting
  shapes, list/index/login/apply rejection, max-job limiting, deduplication, and
  location scoping.
