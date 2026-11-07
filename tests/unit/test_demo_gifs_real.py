"""Guard the demo GIFs embedded in README/docs against placeholder images.

96 source guides once embedded 1x1-pixel, ~42-byte GIFs, so readers saw nothing
where a guide promised a demo. Every GIF referenced from the top-level markdown
files (README included) or ``docs/**`` must exist, be a decodable GIF whose
logical screen is at least 200x100 px, and weigh at least 2 KB. Re-render source
demos with ``uv run python scripts/render_source_demos.py`` (see CONTRIBUTING).
"""

from __future__ import annotations

import io
import re
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MIN_WIDTH = 200
MIN_HEIGHT = 100
MIN_BYTES = 2 * 1024
GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
GIF_REFERENCE = re.compile(
    r"!\[[^\]]*\]\(\s*<?(?P<markdown>[^)\s>]+?\.gif)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)"
    r"|<img\b[^>]*?\bsrc=[\"'](?P<html>[^\"']+?\.gif)[\"']",
    re.IGNORECASE,
)


def _markdown_files() -> list[Path]:
    """Return README and the other top-level docs plus everything under ``docs/``."""
    return sorted({*ROOT.glob("*.md"), *ROOT.glob("docs/**/*.md")})


def _gif_references() -> dict[Path, list[str]]:
    """Map each local GIF embedded in the markdown files to the files embedding it."""
    references: dict[Path, list[str]] = {}
    for markdown in _markdown_files():
        for match in GIF_REFERENCE.finditer(markdown.read_text(encoding="utf-8")):
            target = match.group("markdown") or match.group("html")
            if "://" in target:
                continue
            gif = (markdown.parent / target).resolve()
            references.setdefault(gif, []).append(markdown.relative_to(ROOT).as_posix())
    return references


def _gif_defects(data: bytes) -> list[str]:
    """Explain why ``data`` is not a real demo GIF; empty when it is one."""
    if data[:6] not in GIF_SIGNATURES or len(data) < 10:
        return [f"not a GIF (starts with {data[:6]!r})"]
    width, height = struct.unpack("<HH", data[6:10])
    defects = []
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        defects.append(f"{width}x{height} px < {MIN_WIDTH}x{MIN_HEIGHT}")
    if len(data) < MIN_BYTES:
        defects.append(f"{len(data)} bytes < {MIN_BYTES}")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
    except (OSError, SyntaxError, ValueError) as exc:
        defects.append(f"does not decode ({exc})")
    return defects


def _gif_bytes(width: int, height: int) -> bytes:
    """Encode a noisy GIF of the given size so it does not compress below 2 KB."""
    image = Image.effect_noise((width, height), 64).convert("P")
    buffer = io.BytesIO()
    image.save(buffer, format="GIF")
    return buffer.getvalue()


def test_scan_covers_readme_and_guides() -> None:
    """The guard must actually see the README hero demo and the guide demos."""
    references = _gif_references()
    embedded = {gif.relative_to(ROOT).as_posix() for gif in references}

    assert "assets/demo/agentic-career-search-demo.gif" in embedded
    assert "assets/demo/adp-source.gif" in embedded
    assert any("README.md" in files for files in references.values())
    assert sum(name.endswith("-source.gif") for name in embedded) > 100


def test_defects_flag_placeholders_and_accept_real_demos() -> None:
    """A 1x1 placeholder, a tiny frame and non-GIF bytes fail; a real frame passes."""
    placeholder = _gif_bytes(1, 1)
    tiny = _gif_bytes(120, 60)

    assert _gif_defects(_gif_bytes(640, 300)) == []
    assert any("1x1 px" in defect for defect in _gif_defects(placeholder))
    assert any("bytes <" in defect for defect in _gif_defects(placeholder))
    assert any("120x60 px" in defect for defect in _gif_defects(tiny))
    assert _gif_defects(b"\x89PNG\r\n\x1a\n" + bytes(4096))[0].startswith("not a GIF")
    assert any("does not decode" in d for d in _gif_defects(_gif_bytes(640, 300)[:2100]))


def test_embedded_gifs_are_real_demos() -> None:
    """Every GIF referenced from README/docs exists and is a real, visible demo."""
    problems = []
    for gif, embedded_in in sorted(_gif_references().items()):
        defects = _gif_defects(gif.read_bytes()) if gif.is_file() else ["missing"]
        if defects:
            where = ", ".join(sorted(set(embedded_in)))
            problems.append(f"{gif.relative_to(ROOT)}: {'; '.join(defects)} (in {where})")

    assert problems == [], (
        f"{len(problems)} GIF(s) embedded in README/docs are not real demos:\n"
        + "\n".join(problems)
    )
