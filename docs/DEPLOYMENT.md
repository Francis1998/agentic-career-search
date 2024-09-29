# Production Deployment Of Job Search Automation

*agentic-career-search — 2024-09-29*

## Overview

This guide covers production deployment of job search automation for the `agentic-career-search` project.

## Prerequisites

- Python 3.10+
- Redis (if using distributed mode)
- Environment variables configured (see `.env.example`)

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env

# Run the autoapply_agent module
python -m autoapply_agent --help
```

## Common Scenarios

### Scenario 1: Basic Job Usage

```python
from autoapply_agent import Job

client = Job(config)
result = client.run()
print(result)
```

### Scenario 2: Advanced Configuration

```python
from autoapply_agent.config import Settings

settings = Settings(
    max_retries=3,
    timeout=30,
    log_level="INFO",
)
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `ConnectionError` | API endpoint unreachable | Check `BASE_URL` in `.env` |
| `TimeoutError` | Request took too long | Increase `timeout` setting |
| `AuthError` | Invalid or expired token | Rotate API key |

## See Also

- [README](../README.md)
- [ARCHITECTURE](../ARCHITECTURE.md)
- [API Reference](./API.md)
