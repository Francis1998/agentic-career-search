"""Generate an animated showcase GIF for the repository README."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1120
HEIGHT = 630
CARD_MARGIN = 48


@dataclass(frozen=True, slots=True)
class Slide:
    """Single demo frame description."""

    accent_color: tuple[int, int, int]
    title: str
    subtitle: str
    bullet_points: tuple[str, ...]


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


def _slides() -> Sequence[Slide]:
    """Return all showcase slides in display order."""

    return (
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
        Slide(
            accent_color=(15, 118, 110),
            title="Operate",
            subtitle="Production-minded quality gates and continuous improvements",
            bullet_points=(
                "ruff + mypy + pytest in CI",
                "Daily cron-driven repo improvement commits",
            ),
        ),
    )


def generate_demo_gif(output_path: Path) -> None:
    """Generate and save the animated demo GIF."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    regular_font_path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    bold_font_path = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    title_font = _load_font(bold_font_path, 66)
    subtitle_font = _load_font(regular_font_path, 34)
    body_font = _load_font(regular_font_path, 28)

    frames = [
        _render_slide(
            slide=slide,
            title_font=title_font,
            subtitle_font=subtitle_font,
            body_font=body_font,
        )
        for slide in _slides()
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


def main() -> None:
    """CLI entrypoint for GIF generation."""

    repository_root = Path(__file__).resolve().parent.parent
    demo_output = repository_root / "assets" / "demo" / "agentic-career-search-demo.gif"
    generate_demo_gif(demo_output)
    print(f"Generated demo GIF at: {demo_output}")


if __name__ == "__main__":
    main()
