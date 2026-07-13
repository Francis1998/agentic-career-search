# ADR-086: Jobvite Public Careers Site Source Adapter

**Date:** 2026-07-13
**Status:** Accepted
**Context:** Job Search Automation — public board adapters

## Context

Jobvite (`jobs.jobvite.com/{company}`) is a widely adopted applicant tracking
system. Its hosted careers site is server-rendered and exposes every posting as
an anchor whose href follows a stable `/{company}/job/{jobId}` shape (also
reachable under a `/careers/{company}/job/{jobId}` prefix), where `jobId` is the
posting's canonical mixed-case alphanumeric identifier (for example
`o0rT3fw7`). The path segment is the *singular* `job`, which distinguishes a
posting from the plural `/{company}/jobs` list page, and the id is the terminal
segment, which excludes the application step (`/job/{jobId}/apply`).

The generic `JsonLdAdapter` (ADR-078) covers boards that emit
`schema.org/JobPosting` JSON-LD, but Jobvite careers sites do not reliably ship
that payload. A dedicated adapter that keys on the posting URL shape provides
deterministic coverage, mirroring the existing greenhouse/lever/ashby/workable/
recruitee/smartrecruiters/teamtailor/personio adapters. Personio (ADR-084) also
uses a singular `/job/{jobId}` shape, but its ids are purely numeric whereas
Jobvite ids are alphanumeric, so a dedicated matcher is warranted.

## Decision

Add a `JobviteAdapter` (`source_type = "jobvite"`, ADR-077 field contract still
applies) that derives `JobCandidate` records from posting anchors.

Parsing rules:

1. **Discovery** — every `<a href>` is inspected. An anchor is a posting only
   when its path contains a singular `job` segment immediately followed by a
   terminal segment matching `^[A-Za-z0-9]{5,}$` (a mixed-case alphanumeric id;
   the minimum length keeps short path words from being mistaken for an id).
   Requiring the id to be terminal deterministically excludes the application
   step (`/job/{jobId}/apply`) and the plural `/jobs` list page.
2. **Field derivation** — `title` is the anchor text; `external_id` is the
   `jobId`; `company` is inferred from the host; `location` is resolved within
   the anchor's nearest posting container (a `class` matching
   `job`/`position`/`posting`) so a posting without its own location does not
   inherit a sibling's; `url` is resolved against the source URL.
3. **Deduplication** — candidates are de-duplicated by resolved URL, and
   `max_jobs <= 0` yields no candidates.

## Consequences

- Jobvite careers sites are covered deterministically by URL shape rather than
  depending on JSON-LD being present.
- Behavior is covered by regression tests in
  `tests/unit/test_jobvite_adapter.py` (field extraction across the plain and
  `/careers`-prefixed variants, plural-list and apply-step rejection, per-posting
  location scoping, zero max).
- Boards that do emit JSON-LD remain served by the vendor-neutral
  `JsonLdAdapter`.
