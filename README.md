# agentic-career-search

![CI](https://github.com/Francis1998/{repo}/actions/workflows/ci.yml/badge.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

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

## License

MIT © [Francis1998](https://github.com/Francis1998)

*Last updated: 2024-08-24*
