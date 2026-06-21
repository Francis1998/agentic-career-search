# agentic-career-search

![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen) ![License](https://img.shields.io/badge/license-MIT-green) ![CI](https://github.com/Francis1998/{repo}/actions/workflows/ci.yml/badge.svg)

> Job Search Automation — powered by modern Python async architecture.

## Features

- **Agent engine** with configurable strategies
- **Job pipeline** with full observability
- **Async-first** design using `asyncio` + `aiohttp`
- **Type-safe** with full `mypy` compliance
- **Production-ready** with Docker, CI/CD, and structured logging

## Quick Start

```bash
git clone https://github.com/Francis1998/agentic-career-search.git
cd agentic-career-search
pip install -e ".[dev]"
cp .env.example .env
python -m autoapply_agent --help
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](ARCHITECTURE.md) | System design and component overview |
| [Configuration](docs/CONFIGURATION.md) | All configuration options |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment guide |
| [Contributing](CONTRIBUTING.md) | Development and PR workflow |
| [Changelog](CHANGELOG.md) | Version history |

## Multi-Repo Daily Automation

```bash
./scripts/daily_review_all_repos.sh
```

This orchestrates daily review-and-commit cycles across:
- `agentic-career-search`
- `multi-bot-agentic`
- `nexus-llm-router`
- `scholar-rag-agent`
- `medagent-core`

## License

MIT © [Francis1998](https://github.com/Francis1998)

*Last updated: 2024-10-15*
