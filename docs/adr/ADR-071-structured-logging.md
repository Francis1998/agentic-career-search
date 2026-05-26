# ADR-071: Structured Logging for agentic-career-search

**Date:** 2026-05-25
**Status:** Accepted
**Context:** Job Search Automation

## Context

The `autoapply_agent` module needs a reliable structured logging solution
that integrates cleanly with our async application pipeline.

## Decision

Use **structlog** for structured logging.

## Considered Alternatives

| Option | Pros | Cons |
|--------|------|------|
| **structlog** (chosen) | Native async, well-maintained | Slightly higher cold-start |
| loguru | Mature ecosystem | Sync-first, harder to integrate |
| stdlib logging | Zero dependencies | Limited features for production |

## Consequences

- All new application components will use `structlog` as the structured logging layer.
- Existing code will be migrated incrementally.
- Added to `pyproject.toml` as a core dependency.
