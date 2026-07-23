# Changelog

All notable changes to **agentic-career-search** are documented here.
Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- `ZohoRecruitAdapter` (`source_type: zoho_recruit`): a dedicated adapter for
  public Zoho Recruit (`*.zohorecruit.com`) careers portals and vanity-domain
  proxies. Postings are recognised by `jobId` / `jid` / `job_id` query ids or
  terminal `/job/{id}` / `/jobs/{id}` / `/careers/{id}` /
  `/Jobs/Careers/{id}` path shapes; apply/login steps and `source=apply` /
  `mode=apply` links are ignored. See ADR-093 and
  `docs/guides/ZOHO_RECRUIT_SOURCE_GUIDE.md`.
- `FreshteamAdapter` (`source_type: freshteam`): public Freshteam careers boards. See ADR-093 and `docs/guides/FRESHTEAM_SOURCE_GUIDE.md`.
- `SuccessFactorsAdapter` (`source_type: successfactors`): a dedicated adapter
  for public SAP SuccessFactors (`*.successfactors.com` / `*.successfactors.eu`)
  careers portals. Postings are recognised by `jobId` / `career_job_req_id`
  query requisitions or terminal `/job/{id}` / `/jobs/{id}` path shapes;
  apply/login steps are ignored. See ADR-090 and
  `docs/guides/SUCCESSFACTORS_SOURCE_GUIDE.md`.
- `OracleTaleoAdapter` (`source_type: oracle_taleo`): a dedicated adapter for
  public Oracle Taleo (`*.taleo.net`) and Oracle Cloud HCM careers portals.
  Postings are recognised by `job=` / `jobId` query requisitions or terminal
  `/job/{id}` / `/jobs/{id}` path shapes; apply/login steps are ignored. See
  ADR-089 and `docs/guides/ORACLE_TALEO_SOURCE_GUIDE.md`.
- `WorkdayAdapter` (`source_type: workday`): a structured-JSON adapter for public
  Workday careers boards (`{tenant}.wd{N}.myworkdayjobs.com`). The listing page
  is a client-rendered SPA, so the adapter POSTs to the public CXS endpoint
  `/wday/cxs/{tenant}/{site}/jobs` (hard page size 20), maps each
  `jobPostings[]` entry onto `{origin}/{locale}/{site}{externalPath}`, and
  captures the trailing `JR…` / `R-…` requisition token as `external_id`. See
  ADR-088 and `docs/guides/WORKDAY_SOURCE_GUIDE.md`.
- `IcimsAdapter` (`source_type: icims`): a dedicated adapter for public iCIMS
  careers portals (`careers-{tenant}.icims.com`, plus vanity-domain proxies).
  Postings are recognised purely by their `/jobs/{jobId}/{slug}/job` URL shape
  (terminal literal `job`, numeric id, slug optional) — so the `/jobs/search`
  grid, the application step, and navigation links are ignored and the numeric
  id is captured as the `external_id`. Titles fall back to the anchor `title`
  attribute when the anchor text is empty. See ADR-087.
- `JobviteAdapter` (`source_type: jobvite`): a dedicated adapter for public
  Jobvite careers sites (`jobs.jobvite.com/{company}`). Postings are recognised
  purely by their terminal *singular* `/job/{jobId}` URL shape (also matched
  under a `/careers/{company}` prefix), where `jobId` is a mixed-case
  alphanumeric id — so the plural `/jobs` list page, the `/job/{jobId}/apply`
  step, and navigation links are ignored and the id is captured as the
  `external_id`. See ADR-086.

### Fixed
- `JobviteAdapter`: empty-text posting anchors that expose the role name on the
  `title` attribute are now kept (mirrors iCIMS `_anchor_title`), instead of
  being dropped because only visible anchor text was considered.
- `SmartRecruitersAdapter`: posting hrefs whose optional title slug uses
  mixed/Title Case (e.g. `744000123456789-Senior-Backend-Engineer`) are
  recognised again. The previous `_JOB_ID_PATTERN` required a strictly
  lowercase slug, so `_is_posting_href` silently dropped those openings.
- `JsonLdAdapter`: `jobLocationType` values expressed as IRIs
  (`https://schema.org/Telecommute`) or CURIEs (`schema:Telecommute`) now
  resolve to `location="Remote"` via the same `_type_term` local-term reduction
  already used for `@type`, instead of requiring the exact bare string
  `TELECOMMUTE`.
- `JsonLdAdapter`: a `Place.address` expressed as a (possibly single-element)
  JSON-LD array of `PostalAddress` objects now yields a location string instead
  of being silently dropped. `jobLocation` already handled a list of Places and
  `hiringOrganization` handled a list of orgs, but `_place_to_string` required
  `address` to be a string or dict — leaving `location=None` for otherwise
  complete postings.
- `JsonLdAdapter`: a `hiringOrganization` expressed as a (possibly
  single-element) JSON-LD array now yields its company name instead of being
  silently dropped. `jobLocation` already handled the array form, but
  `hiringOrganization` did not, so a wrapped organization name was lost and the
  company fell back to the host-derived token.
- `JsonLdAdapter`: `JobPosting` blocks whose `@type` is a fully-qualified IRI
  (`https://schema.org/JobPosting`) or a context-prefixed CURIE
  (`schema:JobPosting`) are now recognised. Only the bare `JobPosting` term was
  matched previously, silently dropping every posting emitted with an IRI/CURIE
  type. Type matching now compares the local term after the final `/` or `:`.
- `JsonLdAdapter`: distinct `JobPosting` blocks that omit their own `url` no
  longer collapse into a single candidate. Such postings previously all fell
  back to `base_url` and were discarded after the first by URL deduplication;
  dedup now keys explicit-url postings by URL and url-less postings by title.
- Bumped the `pillow` dev-dependency floor to `>=12.3.0` so the scheduled
  Security Scan (`pip-audit`) no longer fails on the five advisories
  (PYSEC-2026-2253..2257) affecting the previously resolved 12.2.0.

### Added
- `BambooHrAdapter` (`source_type: bamboohr`): the package's first structured-JSON
  source adapter, for public BambooHR hosted careers boards
  (`{tenant}.bamboohr.com`). BambooHR careers pages are client-rendered, so the
  adapter reads the tenant's public `/careers/list` JSON endpoint directly and
  maps each opening to `/careers/{id}`. Handles object and string locations plus
  the `isRemote` flag, and skips blank-id rows that would otherwise collapse
  distinct postings under URL dedup. See ADR-085.
- `PersonioAdapter` (`source_type: personio`): a dedicated adapter for public
  Personio careers sites (`{tenant}.jobs.personio.de` / `.com`), the dominant
  ATS across DACH/EU employers. Postings are recognised purely by their terminal
  *singular* `/job/{jobId}` URL shape (an optional hyphenated title slug may
  trail the id), so the plural `/jobs` list page, the `/job/{jobId}/apply`
  application step, and navigation links are ignored and the numeric posting id
  is captured as the `external_id`. See ADR-084.
- `TeamtailorAdapter` (`source_type: teamtailor`): a dedicated adapter for public
  Teamtailor careers sites (`{company}.teamtailor.com`). Postings are recognised
  purely by their terminal `/jobs/{jobId}-{slug}` URL shape (also matched under a
  custom-domain `/careers` prefix), so the jobs list page, application forms, and
  navigation links are ignored and the numeric posting id is captured as the
  `external_id`. See ADR-083.
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
- Posting location resolution misread a `relocation` badge as the posting's
  location. The shared lookup selected any element whose `class` merely
  *contained* the substring `location` (`[class*=location]`), so a posting
  advertising relocation assistance surfaced that text as its location even when
  no real location element was present. Location is now resolved only from a
  `class` token that *is* `location` (optionally hyphen/underscore-delimited,
  e.g. `job-location`), via a shared `find_location_text` helper reused by the
  Ashby, Workable, Recruitee, SmartRecruiters, and Teamtailor adapters.
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
