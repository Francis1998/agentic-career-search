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
- **Source adapters** get a row in [docs/SUPPORTED_SOURCES.md](docs/SUPPORTED_SOURCES.md)
  and a guide whose demo GIF is rendered from the adapter (see below).
- Describe the current model stack only (see the README's *LLM enrichment* section);
  don't advertise retired models.

## Re-rendering a source demo GIF

Most source guides (`docs/guides/*_SOURCE_GUIDE.md`) embed
`assets/demo/{slug}-source.gif`, a terminal transcript of the adapter's real
`fetch_jobs` replayed over its recorded unit-test fixture through an
`httpx.MockTransport` - no network. After changing an adapter, its fixture, or the
guide's `POST /source-configs` example, re-render and commit the GIF:

```bash
uv run python scripts/render_source_demos.py --dry-run adp  # preview the transcript
uv run python scripts/render_source_demos.py adp            # rewrite assets/demo/adp-source.gif
uv run python scripts/render_source_demos.py                # every demo listed in SOURCE_DEMOS
```

- The source config comes from the guide's `curl ... /source-configs -d '{...}'`
  example, which must pass `SourceConfigCreate` and use only keys the API reads.
- The page served for `GET base_url` is the single `*_SAMPLE_HTML` constant in
  `tests/unit/test_{slug}_adapter.py`; any other request aborts the render.
- For a new adapter, add the slug to `SOURCE_DEMOS` in the script. Output is
  byte-for-byte reproducible on the same machine; it uses Menlo on macOS (DejaVu Sans
  Mono on Linux), so re-rendering elsewhere changes pixels, not content.
- `tests/unit/test_demo_gifs_real.py` fails if any GIF embedded in README/docs is
  missing, not a GIF, smaller than 200×100 px, or under 2 KB.

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
