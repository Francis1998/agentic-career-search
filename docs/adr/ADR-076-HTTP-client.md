# ADR-076: Http Client for agentic-career-search

**Date:** 2024-03-23
**Status:** Accepted
**Context:** Job Search Automation

## Context

The `autoapply_agent` module needs a reliable HTTP client solution
that integrates cleanly with our async workflow pipeline.

## Decision

Use **httpx (async)** for HTTP client.

## Considered Alternatives

| Option | Pros | Cons |
|--------|------|------|
| **httpx (async)** (chosen) | Native async, well-maintained | Slightly higher cold-start |
| aiohttp | Mature ecosystem | Sync-first, harder to integrate |
| requests | Zero dependencies | Limited features for production |

## Consequences

- All new workflow components will use `httpx (async)` as the HTTP client layer.
- Existing code will be migrated incrementally.
- Added to `pyproject.toml` as a core dependency.
