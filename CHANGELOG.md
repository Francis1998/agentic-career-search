# Changelog

All notable changes to **agentic-career-search** are documented here.
Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- `JsonLdAdapter` (`source_type: jsonld`): a vendor-neutral source adapter that
  extracts `schema.org/JobPosting` structured data from embedded JSON-LD, so any
  board publishing Google-Jobs data (Ashby, SmartRecruiters, Workable, custom
  career sites) is supported without a bespoke scraper. See ADR-078.

### Fixed
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
