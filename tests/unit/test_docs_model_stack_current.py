"""Guard user-facing prose against retired model-stack boilerplate.

Guides, catalogs, and docstrings used to say enrichment can use
"GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2" long after the LLM defaults
moved to the GPT-6, Claude 5.5, Gemini 4, and Kimi K3.1 families. Historical
records (CHANGELOG, daily/badge/PR logs, release notes, and ADRs, which record the
context of past decisions) are exempt; tests are not scanned. Lines that announce
a retirement or deprecation (e.g. "Kimi K2 models are being retired") may name
the retired model.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RETIRED_PROSE = re.compile(
    r"\bGPT-5\.\d\b|\bGPT-4o\b|\bClaude\s+(?:Sonnet|Opus)\s+4\.\d\b"
    r"|\bSonnet\s+4\.6\b|\bKimi\s+K2\b(?!\.\d)|\bGemini\s+2\.5\b"
)
RETIREMENT_NOTICE = re.compile(r"\bretir(?:ed|ing|ement)\b|\bdeprecat", re.IGNORECASE)

EXEMPT = {
    Path("CHANGELOG.md"),
    Path("DAILY_IMPROVEMENTS.md"),
    Path("docs/PULL_SHARK_LOG.md"),
    Path("docs/BADGE_LOG.md"),
}
EXEMPT_DIRS = {Path("docs/releases"), Path("docs/adr")}


def _prose_files() -> list[Path]:
    """Return the user-facing docs and non-test sources to scan."""
    files = [*ROOT.glob("*.md"), *ROOT.glob("docs/**/*.md")]
    files += [*ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/**/*.py")]
    return sorted(
        p
        for p in files
        if p.relative_to(ROOT) not in EXEMPT
        and not any(parent in EXEMPT_DIRS for parent in p.relative_to(ROOT).parents)
    )


def test_scan_covers_guides_and_sources() -> None:
    """The guard must actually see the guides, catalog, and services."""
    rels = {p.relative_to(ROOT).as_posix() for p in _prose_files()}

    assert "README.md" in rels
    assert "docs/USE_CASE_CATALOG.md" in rels
    assert "src/autoapply_agent/services/llm_enrichment.py" in rels
    assert not any(r.startswith("docs/adr/") for r in rels)
    assert sum(r.startswith("docs/guides/") for r in rels) > 100


def test_retirement_notices_may_name_retired_models() -> None:
    """Deprecation notices stay legal; boilerplate model stacks do not."""
    notice = "Kimi K2 models are being retired."
    boilerplate = "Optional polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**."

    assert RETIRED_PROSE.search(notice) and RETIREMENT_NOTICE.search(notice)
    assert RETIRED_PROSE.search(boilerplate) and not RETIREMENT_NOTICE.search(boilerplate)


def test_no_retired_model_stack_in_prose() -> None:
    """Docs and docstrings name the current model stack."""
    offenders = [
        f"{path.relative_to(ROOT)}:{lineno}: {line.strip()[:120]}"
        for path in _prose_files()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if RETIRED_PROSE.search(line) and not RETIREMENT_NOTICE.search(line)
    ]

    assert offenders == [], "retired model names in prose:\n" + "\n".join(offenders[:40])
