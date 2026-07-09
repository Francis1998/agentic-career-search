# Changelog

All notable changes to **agentic-career-search** are documented here.
Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- `SmartRecruitersAdapter` (`source_type: smartrecruiters`): a dedicated adapter
  for public SmartRecruiters careers sites (`jobs.smartrecruiters.com/{company}`).
  Postings are recognised purely by their `/{company}/{jobId}-{slug}` URL shape,
  so careers-site navigation and legal links are ignored and the numeric posting
  id is captured as the `external_id`. See ADR-082.
- `RecruiteeAdapter` (`source_type: recruitee`): a dedicated adapter for public
  Recruitee careers sites (`{company}.recruitee.com`). Postings are recognised
  purely by their `/o/{slug}` URL shape, so careers-site navigation and legal
  links are ignored and the posting slug is captured as the `external_id`.
  See ADR-081.
- `WorkableAdapter` (`source_type: workable`): a dedicated adapter for public
  Workable job boards (`apply.workable.com/{company}`). Postings are recognised
  purely by their `/{company}/j/{shortcode}` URL shape, so board navigation and
  legal links are ignored and the posting shortcode is captured as the
  `external_id`. See ADR-080.
- `AshbyAdapter` (`source_type: ashby`): a dedicated adapter for public Ashby
  job boards (`jobs.ashbyhq.com/{org}`). Postings are recognised purely by their
  `/{org}/{uuid}` URL shape, so board navigation and legal links are ignored and
  the posting UUID is captured as the `external_id`. See ADR-079.
- `JsonLdAdapter` (`source_type: jsonld`): a vendor-neutral source adapter that
  extracts `schema.org/JobPosting` structured data from embedded JSON-LD, so any
  board publishing Google-Jobs data (SmartRecruiters, Workable, custom career
  sites) is supported without a bespoke scraper. See ADR-078.

### Fixed
- `LeverAdapter` fallback anchor matching (used when the primary `div.posting`
  selector is absent, e.g. alternative or client-rendered board markup) searched
  for a `/jobs/` path segment that real Lever posting URLs
  (`jobs.lever.co/{company}/{uuid}`) never contain, so every posting was silently
  dropped. The fallback now recognises the true trailing-UUID posting shape while
  still accepting a whole `jobs` path segment used by some embedded board variants.
- `GreenhouseAdapter` fallback anchor matching accepted any href containing the
  bare substring `/job`, so careers navigation links such as `/job_alerts` or
  `/jobseekers/faq` surfaced as phantom job candidates on boards that omit
  `.opening` containers. Matching now requires a whole `jobs` path segment (or a
  `gh_jid` query parameter), keeping only genuine postings.
- `JsonLdAdapter` left the location unset for remote-only postings that expressed
  `jobLocationType` as a single-element list (`["TELECOMMUTE"]`) rather than the
  bare string. JSON-LD permits any property to be an array, so both forms are
  now recognised and resolve to `Remote`.
- LLM enrichment silently dropped summaries when an OpenAI-compatible gateway
  (LiteLLM, vLLM, OpenRouter) returned `choices[0].message.content` as a list of
  structured content parts (`[{"type": "text", "text": ...}]`) instead of a bare
  string. The normalizer now extracts and joins the `text` of each part.
- Greenhouse adapter collapsed word boundaries when a title or location
  contained nested inline markup (e.g. `Senior <span>Backend</span> Engineer`
  became `SeniorBackendEngineer`); text is now joined with a space, matching the
  Lever adapter.

## [v0.4.12] — 2025-09-12

### Added
- Extended crawler module with improved error handling
- Added structured logging for application operations
- New unit tests covering edge cases in workflow pipeline

### Changed
- Refactored retry logic to use exponential backoff with jitter
- Improved type annotations across core modules
- Updated dependency pins to latest stable versions

### Fixed
- Resolved race condition in async crawler handler
- Fixed incorrect application timeout calculation

## [v0.1.0] — 2025-08-22

### Added
- Initial project scaffold with job search automation core
- Basic autoapply_agent implementation
- README and setup documentation
