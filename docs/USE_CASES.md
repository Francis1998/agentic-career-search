# Use Cases

Practical scenarios for driving `agentic-career-search` end to end. Each example
assumes the package is installed (`pip install -e ".[dev]"`) and that source
configurations have been seeded (`python scripts/seed_source_configs.py`).

## 1. Aggregate roles across many ATS providers

The pipeline ships dedicated adapters for the applicant tracking systems (ATS)
that host most public careers pages, plus a generic `schema.org` JSON-LD adapter
that works against any board publishing structured `JobPosting` data:

| Adapter | `source_type` | Recognises |
| --- | --- | --- |
| Greenhouse | `greenhouse` | `boards.greenhouse.io/{company}` job links |
| Lever | `lever` | `jobs.lever.co/{company}` postings |
| Ashby | `ashby` | `jobs.ashbyhq.com/{company}` postings |
| Workable | `workable` | `{company}.workable.com` postings |
| Recruitee | `recruitee` | `{company}.recruitee.com` offers |
| SmartRecruiters | `smartrecruiters` | `careers.smartrecruiters.com/{company}` |
| Teamtailor | `teamtailor` | `{company}.teamtailor.com` jobs |
| Personio | `personio` | `{tenant}.jobs.personio.*` singular `/job/{id}` |
| BambooHR | `bamboohr` | `{tenant}.bamboohr.com` `/careers/list` JSON |
| Jobvite | `jobvite` | `jobs.jobvite.com/{company}/job/{id}` |
| Generic JSON-LD | `jsonld` | any page embedding `JobPosting` structured data |

Because every adapter normalises into the same `JobCandidate` shape (external id,
title, location, company, url), a single run can fan out across providers and
deduplicate the combined result set by URL.

## 2. Add a company whose board is not a first-class adapter

Most modern boards emit `schema.org/JobPosting` JSON-LD so their roles surface in
Google Jobs. Point the `jsonld` adapter at such a page and it will extract the
postings without a bespoke scraper — the adapter recognises the bare `JobPosting`
term as well as the fully-qualified IRI (`https://schema.org/JobPosting`) and
context-prefixed CURIE (`schema:JobPosting`) type forms.

## 3. Run the safety-gated decision loop

The decision engine, state machine, and event log record every transition so a
run is fully auditable. Consult [ARCHITECTURE](adr/) for the agentic pillars and
[CONFIGURATION](CONFIGURATION.md) for the environment variables that gate
outbound requests and rate limits.

## 4. Extend with a new source

1. Subclass `CareerSourceAdapter` in `src/autoapply_agent/adapters/`.
2. Recognise postings by their terminal URL shape (prefer whole-segment matches
   over loose substrings) and return `JobCandidate` objects.
3. Register the `SourceType`, wire it in `main.py`, and seed a config in
   `scripts/seed_source_configs.py`.
4. Add unit tests that parse representative fixture HTML/JSON, and record the
   decision in a new `docs/adr/ADR-0XX-*.md`.

See the existing adapters for the established pattern; the newest
(`bamboohr.py`, `jobvite.py`) show the JSON and singular-path URL shapes.
