# Contributing to agentic-career-search

Thank you for considering a contribution!

## Development Setup

```bash
git clone https://github.com/Francis1998/agentic-career-search.git
cd agentic-career-search
uv sync --extra dev --frozen
uvx pre-commit install   # optional git hooks (.pre-commit-config.yaml)
```

## Running the checks CI runs

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```

## Coding Standards

- Python 3.11+
- Type annotations on all functions
- Google-style docstrings
- Ruff for linting and formatting (`uv run ruff check . && uv run ruff format .`)

## Where new content goes

- **Advisors, use cases and demo GIFs** go to [docs/USE_CASE_CATALOG.md](docs/USE_CASE_CATALOG.md),
  not the README: add the service, its tests and a `docs/guides/*_GUIDE.md`, then a
  catalog row (and GIF) there. The README stays focused on the core product.
- **Source adapters** get a row in [docs/SUPPORTED_SOURCES.md](docs/SUPPORTED_SOURCES.md).
- Describe the current model stack only (see the README's *LLM enrichment* section);
  don't advertise retired models.

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. Ensure tests pass and coverage stays above 80%
3. Update relevant documentation
4. Open a PR with a clear description of the change

## Commit Message Format

```
<type>(<scope>): <short summary>

type: feat | fix | docs | refactor | test | chore
```

*Updated: 2026-11-07*
