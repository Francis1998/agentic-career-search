# ADR-088: Workday Public CXS JSON Source Adapter

**Date:** 2026-07-16
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Workday (`{tenant}.wd{N}.myworkdayjobs.com`) hosts the majority of large-
enterprise career sites (NVIDIA, Accenture Federal, Leidos, and peers). The
public listing page is a client-rendered SPA: scraping static HTML yields no
postings. The SPA itself talks to Workday's public Candidate Experience Service
(CXS) at:

```
POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
Body: {"appliedFacets": {}, "limit": 20, "offset": N, "searchText": ""}
```

No authentication is required for public boards. The hard page size is **20** —
requesting a larger `limit` returns an empty `jobPostings` array with no error,
which looks identical to "end of list". Each entry carries `title`,
`locationsText`, and `externalPath` (e.g.
`/job/US-CA-Santa-Clara/Role-Title_JR2018189`); the public detail URL is
`{origin}/{locale}/{site}{externalPath}`.

BambooHR (ADR-085) already proved structured-JSON adapters. Workday is the
second JSON source and the first that issues a POST against a public board API —
closing the largest remaining ATS coverage gap versus popular scrapers such as
[jobo.world/ats/workday](https://jobo.world/ats/workday) and career-ops.

## Decision

Add a `WorkdayAdapter` (`source_type = "workday"`, ADR-077 field contract still
applies) that derives `JobCandidate` records from the public CXS listing API.

Parsing rules:

1. **Board derivation** — tenant comes from the `{tenant}.wd{N}.myworkdayjobs.com`
   host; site is the first non-locale path segment; locale defaults to `en-US`
   when omitted. The CXS URL is always
   `{origin}/wday/cxs/{tenant}/{site}/jobs`.
2. **Pagination** — POST pages of at most 20 postings, advancing `offset` by the
   number received, until `max_jobs` is satisfied or a short page arrives.
3. **Field derivation** — `title` / `locationsText` map directly; `external_id`
   is the requisition token after the final `_` in `externalPath` (`JR…` /
   `R-…`); `url` is `{origin}/{locale}/{site}{externalPath}`; `company` is
   inferred from the host.
4. **Rejection** — non-Workday hosts and careers URLs missing a site slug raise
   `SourceAdapterError`; blank title/path rows are skipped.

## Consequences

- Enterprise Workday boards are covered without headless browsers or vendor API
  keys.
- Behavior is covered by regression tests in
  `tests/unit/test_workday_adapter.py` (field extraction, locale defaulting,
  blank-row skip, host rejection, invalid JSON, zero max).
- Operators configure `source_type: workday` with any public careers URL for the
  tenant/site; see `docs/guides/WORKDAY_SOURCE_GUIDE.md`.
