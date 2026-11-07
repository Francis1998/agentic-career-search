"""Generate animated showcase GIF assets for the repository README.

Two kinds of decks are rendered with Pillow into ``assets/demo/``:

* :class:`Deck` — title/bullet slides;
* :class:`TranscriptDeck` — a terminal replay of a REAL captured transcript (lines that
  start with ``$ `` are typed as commands, every other line is revealed as their
  output), so the GIF shows exactly what the commands printed.

Usage::

    uv run python scripts/generate_demo_gif.py                       # every deck
    uv run python scripts/generate_demo_gif.py --only mcp-server.gif # selected decks
"""

from __future__ import annotations

import argparse
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1120
HEIGHT = 630
CARD_MARGIN = 48
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

TERMINAL_FONT_CANDIDATES: tuple[Path, ...] = (
    Path("/System/Library/Fonts/Menlo.ttc"),
    Path("/System/Library/Fonts/Monaco.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSansMono.ttf"),
)
TERMINAL_BACKGROUND = (13, 17, 23)
TERMINAL_BAR = (33, 38, 45)
TERMINAL_TEXT = (201, 209, 217)
TERMINAL_TITLE = (139, 148, 158)
TERMINAL_PROMPT = (88, 166, 255)
TERMINAL_COMMAND = (126, 231, 135)
TERMINAL_DOTS = ((255, 95, 86), (255, 189, 46), (39, 201, 63))


@dataclass(frozen=True, slots=True)
class Slide:
    """Single demo frame description."""

    accent_color: tuple[int, int, int]
    title: str
    subtitle: str
    bullet_points: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Deck:
    """Represents one GIF deck with destination and slides."""

    output_filename: str
    slides: tuple[Slide, ...]


@dataclass(frozen=True, slots=True)
class TranscriptDeck:
    """Terminal GIF replaying a real captured transcript.

    Attributes:
        output_filename: GIF file name under ``assets/demo/``.
        transcript: Transcript path relative to the repository root.
        title: Window title shown in the terminal bar.
        highlights: Output-line prefixes and the colour used for those lines.
        pause_before: Output-line prefixes that get a reading pause before them.
        columns: Terminal width in characters (long lines wrap).
        rows: Visible terminal rows (the view scrolls).
    """

    output_filename: str
    transcript: Path
    title: str
    highlights: tuple[tuple[str, tuple[int, int, int]], ...] = ()
    pause_before: tuple[str, ...] = ()
    columns: int = 120
    rows: int = 32


def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a truetype font with fallback to PIL default font."""

    try:
        return ImageFont.truetype(str(font_path), size=size)
    except OSError:
        return ImageFont.load_default()


def _wrap_lines(text: str, max_chars: int) -> list[str]:
    """Wrap text into lines by approximate character count."""

    words = text.split()
    lines: list[str] = []
    current_line: list[str] = []
    current_len = 0
    for word in words:
        projected_len = current_len + len(word) + (1 if current_line else 0)
        if projected_len > max_chars and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_len = len(word)
        else:
            current_line.append(word)
            current_len = projected_len
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _render_slide(
    slide: Slide,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    subtitle_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> Image.Image:
    """Render one slide image for GIF composition."""

    base_color = (10, 14, 29)
    panel_color = (16, 23, 42)
    text_primary = (241, 245, 249)
    text_secondary = (203, 213, 225)
    accent_text = (56, 189, 248)

    image = Image.new("RGB", (WIDTH, HEIGHT), base_color)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (CARD_MARGIN, CARD_MARGIN, WIDTH - CARD_MARGIN, HEIGHT - CARD_MARGIN),
        radius=28,
        fill=panel_color,
    )
    draw.rounded_rectangle(
        (CARD_MARGIN, CARD_MARGIN, WIDTH - CARD_MARGIN, CARD_MARGIN + 18),
        radius=10,
        fill=slide.accent_color,
    )

    title_bbox = draw.textbbox((0, 0), slide.title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(
        ((WIDTH - title_width) // 2, 120),
        slide.title,
        fill=text_primary,
        font=title_font,
    )

    subtitle_lines = _wrap_lines(slide.subtitle, max_chars=58)
    subtitle_y = 220
    for line in subtitle_lines:
        line_bbox = draw.textbbox((0, 0), line, font=subtitle_font)
        line_width = line_bbox[2] - line_bbox[0]
        draw.text(
            ((WIDTH - line_width) // 2, subtitle_y),
            line,
            fill=text_secondary,
            font=subtitle_font,
        )
        subtitle_y += 44

    bullets_y = 335
    for bullet in slide.bullet_points:
        bullet_line = f"- {bullet}"
        draw.text((150, bullets_y), bullet_line, fill=text_secondary, font=body_font)
        bullets_y += 48

    footer_text = "agentic-career-search"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=subtitle_font)
    footer_width = footer_bbox[2] - footer_bbox[0]
    draw.text(
        ((WIDTH - footer_width) // 2, HEIGHT - 110),
        footer_text,
        fill=accent_text,
        font=subtitle_font,
    )

    return image


def _transcript_decks() -> Sequence[TranscriptDeck]:
    """Return the terminal decks rendered from captured transcripts."""

    return (
        TranscriptDeck(
            output_filename="mcp-server.gif",
            transcript=Path("docs/guides/MCP_SERVER_DEMO_TRANSCRIPT.txt"),
            title="agentic-career-search: read-only MCP server (stdio, JSON-RPC)",
            highlights=(("→ ", (121, 192, 255)), ("← ", (255, 166, 87))),
            pause_before=("→ ", "legacy client", "stdin closed"),
        ),
    )


def _terminal_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the first available monospace font, falling back to PIL's default."""

    for candidate in TERMINAL_FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _terminal_rows(lines: Sequence[str], columns: int) -> list[tuple[str, str, bool]]:
    """Wrap transcript lines into ``(kind, text, wrapped)`` rows.

    ``kind`` is ``cmd`` for typed commands and ``out`` for output; ``wrapped`` marks the
    continuation rows of a line longer than ``columns``.
    """

    rows: list[tuple[str, str, bool]] = []
    for line in lines:
        kind = "cmd" if line.startswith("$ ") else "out"
        indent = " " * (len(line) - len(line.lstrip()) + 2)
        pieces = textwrap.wrap(
            line, width=columns, subsequent_indent=indent, break_on_hyphens=False
        ) or [""]
        rows.append((kind, pieces[0], False))
        rows.extend((kind, piece, True) for piece in pieces[1:])
    return rows


def _render_transcript_gif(deck: TranscriptDeck, output_path: Path) -> None:
    """Render one terminal replay GIF from a captured transcript."""

    lines = (REPOSITORY_ROOT / deck.transcript).read_text(encoding="utf-8").splitlines()
    font = _terminal_font(15)
    char_width = font.getlength("M")
    line_height = 21
    padding = 16
    bar_height = 30
    width = WIDTH
    height = bar_height + 2 * padding + line_height * deck.rows
    columns = min(deck.columns, int((width - 2 * padding) // char_width))
    # Each row keeps the colour of the line it belongs to (wrapped rows included).
    coloured: list[tuple[str, str, tuple[int, int, int]]] = []
    fill = TERMINAL_TEXT
    for kind, text, wrapped in _terminal_rows(lines, columns):
        if kind == "cmd":
            fill = TERMINAL_COMMAND
        elif not wrapped:
            fill = next(
                (colour for prefix, colour in deck.highlights if text.startswith(prefix)),
                TERMINAL_TEXT,
            )
        coloured.append(("prompt" if kind == "cmd" and not wrapped else "text", text, fill))

    def draw(shown: Sequence[tuple[str, str, tuple[int, int, int]]]) -> Image.Image:
        image = Image.new("RGB", (width, height), TERMINAL_BACKGROUND)
        canvas = ImageDraw.Draw(image)
        canvas.rectangle((0, 0, width, bar_height), fill=TERMINAL_BAR)
        for index, dot in enumerate(TERMINAL_DOTS):
            left = 14 + index * 20
            canvas.ellipse((left, 10, left + 11, 21), fill=dot)
        canvas.text((80, 7), deck.title, font=font, fill=TERMINAL_TITLE)
        top = bar_height + padding
        for style, text, row_fill in shown:
            if style == "prompt":
                canvas.text((padding, top), "$", font=font, fill=TERMINAL_PROMPT)
                canvas.text((padding + 2 * char_width, top), text[2:], font=font, fill=row_fill)
            else:
                canvas.text((padding, top), text, font=font, fill=row_fill)
            top += line_height
        return image

    frames: list[Image.Image] = [draw([])]
    durations: list[int] = [700]
    printed: list[tuple[str, str, tuple[int, int, int]]] = []
    first_row = 0

    def show(
        row: tuple[str, str, tuple[int, int, int]],
    ) -> list[tuple[str, str, tuple[int, int, int]]]:
        """Rows on screen once ``row`` is printed; scrolls half a screen at a time."""

        nonlocal first_row
        if len(printed) + 1 - first_row > deck.rows:
            # Scrolling redraws every pixel, so jump in big steps: GIF frames then only
            # store the newly printed rows in between.
            first_row = max(first_row + deck.rows // 2, len(printed) + 1 - deck.rows)
        return [*printed[first_row:], row]

    for style, text, row_fill in coloured:
        if style == "prompt":
            body = text[2:]
            step = max(1, len(body) // 8)
            for end in range(step, len(body), step):
                frames.append(draw(show((style, "$ " + body[:end], row_fill))))
                durations.append(45)
            frames.append(draw(show((style, text, row_fill))))
            durations.append(500)
        else:
            if text.startswith(deck.pause_before):
                durations[-1] += 800
            frames.append(draw(show((style, text, row_fill))))
            durations.append(90)
        printed.append((style, text, row_fill))
    durations[-1] = 5000

    # One shared palette keeps colours stable and lets Pillow store only frame deltas.
    # Solid swatches guarantee every UI colour a palette entry, however rare it is.
    swatch_colours = [
        TERMINAL_BACKGROUND,
        TERMINAL_BAR,
        TERMINAL_TEXT,
        TERMINAL_TITLE,
        TERMINAL_PROMPT,
        TERMINAL_COMMAND,
        *TERMINAL_DOTS,
        *(colour for _, colour in deck.highlights),
    ]
    stripe = 24
    palette_source = Image.new("RGB", (width, height + stripe * len(swatch_colours)))
    palette_source.paste(frames[-1], (0, 0))
    for index, swatch in enumerate(swatch_colours):
        top = height + index * stripe
        palette_source.paste(swatch, (0, top, width, top + stripe))
    palette = palette_source.quantize(colors=48, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(
        output_path,
        save_all=True,
        append_images=indexed[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )


def _decks() -> Sequence[Deck]:
    """Return all demo decks rendered into GIF assets."""

    return (
        Deck(
            output_filename="agentic-career-search-demo.gif",
            slides=(
                Slide(
                    accent_color=(37, 99, 235),
                    title="Agentic Career Search",
                    subtitle="Autonomous AI-agent orchestration for job discovery workflows",
                    bullet_points=(
                        "Observe -> Decide -> Act architecture",
                        "Deterministic and traceable decisions",
                    ),
                ),
                Slide(
                    accent_color=(79, 70, 229),
                    title="Observe",
                    subtitle="Adapter tools ingest public Greenhouse and Lever career pages",
                    bullet_points=(
                        "Source abstraction for extensibility",
                        "Timeout-aware external fetch operations",
                    ),
                ),
                Slide(
                    accent_color=(124, 58, 237),
                    title="Decide",
                    subtitle="AgentDecisionEngine computes score, priority tier, and rationale",
                    bullet_points=(
                        "Matched query-term extraction",
                        "Explainable triage policy output",
                    ),
                ),
                Slide(
                    accent_color=(14, 116, 144),
                    title="Act",
                    subtitle="Worker persists jobs, plan steps, and event timeline entries",
                    bullet_points=(
                        "Durable run and event memory",
                        "Operational controls with cancellation",
                    ),
                ),
            ),
        ),
        Deck(
            output_filename="llm-provider-flow.gif",
            slides=(
                Slide(
                    accent_color=(126, 34, 206),
                    title="LLM Enrichment Layer",
                    subtitle="Provider-agnostic enrichment for AI decision context",
                    bullet_points=(
                        "Gemini API",
                        "Kimi (Moonshot) API",
                        "Claude API",
                        "GPT-compatible API",
                    ),
                ),
                Slide(
                    accent_color=(147, 51, 234),
                    title="Gemini",
                    subtitle="Consumes Google Gemini responses for compact role-fit summaries",
                    bullet_points=(
                        "Model configurable via GEMINI_MODEL",
                        "Graceful fallback when key is absent",
                    ),
                ),
                Slide(
                    accent_color=(30, 64, 175),
                    title="Kimi",
                    subtitle="Consumes Kimi outputs through OpenAI-compatible chat endpoint",
                    bullet_points=(
                        "Configurable KIMI_BASE_URL",
                        "Integrated into worker event timeline",
                    ),
                ),
                Slide(
                    accent_color=(15, 23, 42),
                    title="Claude",
                    subtitle="Consumes Anthropic Claude messages for enrichment summaries",
                    bullet_points=(
                        "Model configurable via CLAUDE_MODEL",
                        "Persisted in job raw.llm_enrichment",
                    ),
                ),
            ),
        ),
        Deck(
            output_filename="ops-reliability-loop.gif",
            slides=(
                Slide(
                    accent_color=(8, 145, 178),
                    title="Reliability Loop",
                    subtitle="AI workflow quality controls designed for production behavior",
                    bullet_points=(
                        "Structured run events and state transitions",
                        "Cancellation, timeout, and bounded scope controls",
                    ),
                ),
                Slide(
                    accent_color=(6, 95, 70),
                    title="Quality Gates",
                    subtitle="Each iteration passes static and runtime checks before shipment",
                    bullet_points=(
                        "ruff + mypy + pytest in CI",
                        "Deterministic tests for core decision paths",
                    ),
                ),
                Slide(
                    accent_color=(22, 101, 52),
                    title="Continuous Improvement",
                    subtitle="Daily automation keeps the repository actively maintained",
                    bullet_points=(
                        "Cron-triggered daily review script",
                        "Automatic improvement commit to main",
                    ),
                ),
            ),
        ),
        Deck(
            output_filename="jazzhr-source.gif",
            slides=(
                Slide(
                    accent_color=(217, 119, 6),
                    title="JazzHR Source Adapter",
                    subtitle="Deterministic discovery for applytojob.com public careers boards",
                    bullet_points=(
                        "Registers source_type=jazzhr",
                        "Parses /apply/{jobId} posting links",
                    ),
                ),
                Slide(
                    accent_color=(234, 88, 12),
                    title="URL Shape Matching",
                    subtitle="Accepts JazzHR posting links with optional human-readable slugs",
                    bullet_points=(
                        "/apply/JAZZ-1234",
                        "/apply/JAZZ-1234/platform-engineer",
                    ),
                ),
                Slide(
                    accent_color=(194, 65, 12),
                    title="Clean Candidates",
                    subtitle="Navigation, search, and deeper application-step links are ignored",
                    bullet_points=(
                        "Scoped location extraction",
                        "Duplicate posting URLs returned once",
                    ),
                ),
            ),
        ),
    )


def _generate_gif(
    output_path: Path,
    slides: Sequence[Slide],
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    subtitle_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Render one GIF from a sequence of slides."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    frames = [
        _render_slide(
            slide=slide,
            title_font=title_font,
            subtitle_font=subtitle_font,
            body_font=body_font,
        )
        for slide in slides
    ]

    first_frame, *rest_frames = frames
    frame_duration_ms = 1600
    durations = [frame_duration_ms for _ in frames]
    first_frame.save(
        output_path,
        save_all=True,
        append_images=rest_frames,
        duration=durations,
        loop=0,
        optimize=True,
    )


def generate_all_demo_gifs(output_dir: Path, only: Sequence[str] = ()) -> list[Path]:
    """Generate deck GIFs into the target directory.

    Args:
        output_dir: Destination directory.
        only: Output file names to render; empty renders every deck.

    Returns:
        Paths of the generated GIFs.
    """

    regular_font_path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    bold_font_path = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    title_font = _load_font(bold_font_path, 66)
    subtitle_font = _load_font(regular_font_path, 34)
    body_font = _load_font(regular_font_path, 28)

    generated_paths: list[Path] = []
    for deck in _decks():
        if only and deck.output_filename not in only:
            continue
        target_path = output_dir / deck.output_filename
        _generate_gif(
            output_path=target_path,
            slides=deck.slides,
            title_font=title_font,
            subtitle_font=subtitle_font,
            body_font=body_font,
        )
        generated_paths.append(target_path)
    for transcript_deck in _transcript_decks():
        if only and transcript_deck.output_filename not in only:
            continue
        target_path = output_dir / transcript_deck.output_filename
        _render_transcript_gif(transcript_deck, target_path)
        generated_paths.append(target_path)
    return generated_paths


def main() -> None:
    """CLI entrypoint for generating demo GIF assets."""

    parser = argparse.ArgumentParser(description="Render the demo GIFs into assets/demo/.")
    parser.add_argument(
        "--only",
        nargs="+",
        default=[],
        metavar="FILE",
        help="Render only these output files (for example mcp-server.gif).",
    )
    args = parser.parse_args()
    demo_output_dir = REPOSITORY_ROOT / "assets" / "demo"
    outputs = generate_all_demo_gifs(demo_output_dir, only=args.only)
    for path in outputs:
        print(f"Generated demo GIF at: {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
