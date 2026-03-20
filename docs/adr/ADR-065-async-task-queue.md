# ADR-065: Async Task Queue for agentic-career-search

**Date:** 2026-03-20
**Status:** Accepted
**Context:** Job Search Automation

## Context

The `autoapply_agent` module needs a reliable async task queue solution
that integrates cleanly with our async application pipeline.

## Decision

Use **Redis Streams** for async task queue.

## Considered Alternatives

| Option | Pros | Cons |
|--------|------|------|
| **Redis Streams** (chosen) | Native async, well-maintained | Slightly higher cold-start |
| Celery + RabbitMQ | Mature ecosystem | Sync-first, harder to integrate |
| asyncio.Queue | Zero dependencies | Limited features for production |

## Consequences

- All new application components will use `Redis Streams` as the async task queue layer.
- Existing code will be migrated incrementally.
- Added to `pyproject.toml` as a core dependency.
