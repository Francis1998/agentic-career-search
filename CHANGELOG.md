# Changelog

All notable changes to **agentic-career-search** are documented here.
Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v0.7.17] — 2024-10-25

### Added
- Extended job module with improved error handling
- Added structured logging for workflow operations
- New unit tests covering edge cases in application pipeline

### Changed
- Refactored retry logic to use exponential backoff with jitter
- Improved type annotations across core modules
- Updated dependency pins to latest stable versions

### Fixed
- Resolved race condition in async job handler
- Fixed incorrect workflow timeout calculation

## [v0.1.0] — 2024-09-20

### Added
- Initial project scaffold with job search automation core
- Basic autoapply_agent implementation
- README and setup documentation
