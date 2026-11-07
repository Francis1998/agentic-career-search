"""Render the source-adapter demo GIFs from real adapter runs over recorded fixtures.

Each ``docs/guides/*_SOURCE_GUIDE.md`` embeds ``assets/demo/{slug}-source.gif``. For
every slug in :data:`SOURCE_DEMOS` this script:

1. reads the source config (``name`` / ``source_type`` / ``base_url``) from the
   guide's ``POST /source-configs`` example;
2. calls the adapter's real ``fetch_jobs`` with the worker defaults while every
   ``httpx.AsyncClient`` is backed by an ``httpx.MockTransport`` that answers the one
   ``GET base_url`` with the adapter's recorded unit-test fixture
   (``tests/unit/test_{slug}_adapter.py::*_SAMPLE_HTML``). Nothing reaches the
   network: any other request aborts the run;
3. renders the transcript (config, request and the normalized ``JobCandidate``
   list: title, company, location, remote flag, URL) as a terminal GIF.

The GIF shows exactly what ``--dry-run`` prints, so the text of any demo can be
reproduced without writing files.

Usage::

    uv run python scripts/render_source_demos.py               # every source demo
    uv run python scripts/render_source_demos.py adp remoteok  # only these
    uv run python scripts/render_source_demos.py --dry-run adp # print, write nothing
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
import math
import re
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from unittest import mock

import httpx
from generate_demo_gif import (
    ACCENT_TEXT,
    BASE_COLOR,
    PANEL_COLOR,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from PIL import Image, ImageDraw, ImageFont
from pydantic import ValidationError

from autoapply_agent.adapters.base import CareerSourceAdapter, JobCandidate
from autoapply_agent.core.config import Settings
from autoapply_agent.schemas.source_configs import SourceConfigCreate
from autoapply_agent.services.job_search import is_remote_location

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "assets" / "demo"
GUIDES_DIR = REPO_ROOT / "docs" / "guides"
SCRIPT = "scripts/render_source_demos.py"
FIXTURE_LABEL = "recorded fixture, no network"

USER_AGENT: str = Settings.model_fields["http_user_agent"].default
TIMEOUT_SECONDS: float = Settings.model_fields["http_timeout_seconds"].default
MAX_JOBS: int = Settings.model_fields["max_jobs_per_source"].default

# Source demos rendered by this script. Other ``*-source.gif`` files are hand-made.
SOURCE_DEMOS: tuple[str, ...] = (
    "adp", "aijobs", "angellist", "applicantpro", "applicantstack", "applied", "arcdev",
    "authenticjobs", "avature", "beamery", "brassring", "builtin", "bullhorn", "careerbuilder",
    "careerplug", "catsone", "ceipal", "clearcompany", "comeet", "cornerstone", "crelate",
    "cryptojobs", "dayforce", "dice", "dover", "dynamitejobs", "eightfold", "eploy",
    "eurotechjobs", "factorial", "flexjobs", "fountain", "fourdayweek", "glassdoor", "handshake",
    "hibob", "himalayas", "hireez", "hireology", "hirevue", "homerun", "indeed", "jibe",
    "jobadder", "jobdiva", "jobgether", "jobspresso", "jobylon", "join", "jooble", "justremote",
    "levelsfyi", "loxo", "manatal", "monster", "naukri", "nodesk", "nofluffjobs", "otta", "pageup",
    "pangian", "paradox", "paycom", "paylocity", "pcrecruiter", "phenom", "polymer", "powertofly",
    "pythonjobs", "radancy", "recruitcrm", "recruiterflow", "reed", "remoteco", "remoteleaf",
    "remoteok", "remotive", "seek", "silkroad", "simplyhired", "softgarden", "talentlyft",
    "themuse", "totaljobs", "trackerrms", "tribepad", "ukg", "vincere", "welcometothejungle",
    "wellfound", "weworkremotely", "workatastartup", "workingnomads", "workintheopen", "yello",
    "ziprecruiter",
)  # fmt: skip

_GIF_MARKER = re.compile(r"assets/demo/(?P<slug>[a-z0-9-]+)-source\.gif")
_GUIDE_TITLE = re.compile(r"^# (?P<name>.+?) Source Guide\s*$", re.MULTILINE)
_CONFIG_PAYLOAD = re.compile(r"curl -X POST \S*/source-configs.*?-d '(?P<json>\{.*?\})'", re.DOTALL)

# Terminal styling: the shared demo palette plus terminal accents.
TITLE_BAR_COLOR = (30, 41, 59)
PROMPT_COLOR = (74, 222, 128)
MUTED_COLOR = (100, 116, 139)
URL_COLOR = (147, 197, 253)
TRAFFIC_LIGHTS = ((255, 95, 86), (255, 189, 46), (39, 201, 63))
STYLE_COLORS: dict[str, tuple[int, int, int]] = {
    "prompt": PROMPT_COLOR,
    "command": TEXT_PRIMARY,
    "comment": MUTED_COLOR,
    "label": ACCENT_TEXT,
    "text": TEXT_SECONDARY,
    "strong": TEXT_PRIMARY,
    "url": URL_COLOR,
    "yes": PROMPT_COLOR,
    "no": MUTED_COLOR,
}
FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Menlo.ttc"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
    Path("C:/Windows/Fonts/consola.ttf"),
)
FONT_SIZE = 13
LINE_HEIGHT = 19
CANVAS_WIDTH = 800
MIN_CANVAS_HEIGHT = 300
WINDOW_MARGIN = 12
TITLE_BAR_HEIGHT = 30
TEXT_PADDING = 16
FRAME_DURATIONS_MS = (1000, 1400, 1400, 5200)

Segment = tuple[str, str]
Line = tuple[Segment, ...]


class DemoError(RuntimeError):
    """Raised when a source demo cannot be resolved or would leave the fixture."""


@dataclass(frozen=True, slots=True)
class SourceDemo:
    """Everything needed to replay one adapter over its recorded fixture."""

    slug: str
    display_name: str
    config: dict[str, str]
    adapter_factory: Callable[[str], CareerSourceAdapter]
    adapter_class_name: str
    fixture_ref: str
    fixture_html: str

    @property
    def base_url(self) -> str:
        """Return the guide's documented ``base_url``."""

        return self.config["base_url"]


@dataclass(frozen=True, slots=True)
class DemoRun:
    """Result of one replayed ``fetch_jobs`` call."""

    demo: SourceDemo
    requests: tuple[httpx.Request, ...]
    jobs: tuple[JobCandidate, ...]


@cache
def _guides_by_slug() -> dict[str, Path]:
    """Index source guides by the ``{slug}-source.gif`` they embed."""

    index: dict[str, Path] = {}
    for guide in sorted(GUIDES_DIR.glob("*_SOURCE_GUIDE.md")):
        hero = _GIF_MARKER.search(guide.read_text(encoding="utf-8"))
        if hero is not None:
            index.setdefault(hero["slug"], guide)
    return index


def _source_config(guide: Path) -> dict[str, str]:
    """Parse and validate the ``POST /source-configs`` example payload of a guide.

    The payload must pass the API's ``SourceConfigCreate`` schema and may only use
    keys the API reads, so a demo never shows a config the service would ignore.
    """

    match = _CONFIG_PAYLOAD.search(guide.read_text(encoding="utf-8"))
    if match is None:
        raise DemoError(f"{guide.name}: no `curl -X POST .../source-configs -d '{{...}}'` example")
    payload = json.loads(match["json"])
    ignored = sorted(set(payload) - set(SourceConfigCreate.model_fields))
    if ignored:
        raise DemoError(f"{guide.name}: source-config example sets keys the API ignores: {ignored}")
    try:
        config = SourceConfigCreate.model_validate(payload)
    except ValidationError as exc:
        raise DemoError(f"{guide.name}: invalid source-config example: {exc}") from exc
    return {
        "name": config.name,
        "source_type": config.source_type.value,
        "base_url": str(payload["base_url"]),
    }


def _adapter_class(slug: str, source_type: str) -> type[CareerSourceAdapter]:
    """Return the adapter class registered for ``source_type`` in the slug's module."""

    module = importlib.import_module(f"autoapply_agent.adapters.{slug.replace('-', '_')}")
    classes = [
        member
        for member in vars(module).values()
        if inspect.isclass(member)
        and issubclass(member, CareerSourceAdapter)
        and member.__module__ == module.__name__
        and getattr(member, "adapter_name", None) == source_type
    ]
    if len(classes) != 1:
        raise DemoError(f"{module.__name__}: expected one adapter named {source_type!r}")
    return classes[0]


def _fixture(slug: str) -> tuple[str, str]:
    """Return ``(reference, html)`` of the adapter test's ``*_SAMPLE_HTML`` fixture."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    module = importlib.import_module(f"tests.unit.test_{slug.replace('-', '_')}_adapter")
    names = [
        name
        for name, value in vars(module).items()
        if name.upper().endswith("_SAMPLE_HTML") and isinstance(value, str)
    ]
    if len(names) != 1:
        raise DemoError(f"{module.__name__}: expected one *_SAMPLE_HTML fixture, got {names}")
    test_file = Path(str(module.__file__)).resolve().relative_to(REPO_ROOT).as_posix()
    return f"{test_file}::{names[0]}", getattr(module, names[0])


def resolve_demo(slug: str) -> SourceDemo:
    """Collect the guide config, adapter class and recorded fixture for ``slug``.

    Args:
        slug: Demo slug, i.e. ``assets/demo/{slug}-source.gif``.

    Returns:
        Resolved source demo.

    Raises:
        DemoError: If the guide, its config example, the adapter or the fixture
            cannot be found unambiguously.
    """

    guide = _guides_by_slug().get(slug)
    if guide is None:
        raise DemoError(f"no docs/guides/*_SOURCE_GUIDE.md embeds assets/demo/{slug}-source.gif")
    title = _GUIDE_TITLE.search(guide.read_text(encoding="utf-8"))
    config = _source_config(guide)
    adapter_class = _adapter_class(slug, config["source_type"])
    fixture_ref, fixture_html = _fixture(slug)
    return SourceDemo(
        slug=slug,
        display_name=title["name"] if title else slug,
        config=config,
        adapter_factory=adapter_class,
        adapter_class_name=adapter_class.__name__,
        fixture_ref=fixture_ref,
        fixture_html=fixture_html,
    )


@contextmanager
def recorded_transport(base_url: str, html: str, requests: list[httpx.Request]) -> Iterator[None]:
    """Back every ``httpx.AsyncClient`` with a mock serving ``html`` for ``GET base_url``.

    Args:
        base_url: The only URL the adapter may request.
        html: Recorded response body.
        requests: Receives every request the adapter sends.

    Yields:
        Nothing; the patch is active inside the ``with`` block.
    """

    real_client = httpx.AsyncClient
    expected = httpx.URL(base_url)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method != "GET" or request.url != expected:
            raise DemoError(f"refusing {request.method} {request.url}: demos replay {base_url}")
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    def client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)  # type: ignore[arg-type]

    with mock.patch.object(httpx, "AsyncClient", client_factory):
        yield


def run_demo(demo: SourceDemo) -> DemoRun:
    """Run the adapter's real ``fetch_jobs`` against its recorded fixture.

    Args:
        demo: Resolved source demo.

    Returns:
        The requests sent and the normalized jobs returned.
    """

    requests: list[httpx.Request] = []
    adapter = demo.adapter_factory(USER_AGENT)
    with recorded_transport(demo.base_url, demo.fixture_html, requests):
        jobs = asyncio.run(adapter.fetch_jobs(demo.base_url, TIMEOUT_SECONDS, MAX_JOBS))
    if not jobs:
        raise DemoError(f"{demo.slug}: the adapter found no jobs in {demo.fixture_ref}")
    return DemoRun(demo=demo, requests=tuple(requests), jobs=tuple(jobs))


def transcript(run: DemoRun) -> list[Line]:
    """Build the terminal transcript of a demo run, one styled line per row.

    Args:
        run: Replayed demo run.

    Returns:
        Lines of ``(text, style)`` segments; joined, they are the ``--dry-run`` output.
    """

    demo = run.demo
    config = demo.config
    fixture_bytes = len(demo.fixture_html.encode("utf-8"))
    rows = [
        (
            job.title,
            job.company or "-",
            job.location or "-",
            "yes" if is_remote_location(job.location) else "no",
        )
        for job in run.jobs
    ]
    headers = ("TITLE", "COMPANY", "LOCATION", "REMOTE")
    widths = [max(len(header), *(len(row[i]) for row in rows)) for i, header in enumerate(headers)]
    index_width = len(str(len(rows)))

    def cells(values: Sequence[str], styles: Sequence[str]) -> list[Segment]:
        segments: list[Segment] = []
        for i, (value, style) in enumerate(zip(values, styles, strict=True)):
            last = i == len(values) - 1
            segments.append((value if last else value.ljust(widths[i] + 2), style))
        return segments

    lines: list[Line] = [
        (("$ ", "prompt"), (f"uv run python {SCRIPT} --dry-run {demo.slug}", "command")),
        ((f"# {demo.display_name} adapter, {FIXTURE_LABEL} (httpx.MockTransport)", "comment"),),
        (
            ("source config  ", "label"),
            (f"name={config['name']}  source_type={config['source_type']}", "text"),
        ),
        (("               ", "label"), (f"base_url={config['base_url']}", "text")),
        (("fixture        ", "label"), (f"{demo.fixture_ref} ({fixture_bytes:,} B)", "text")),
    ]
    for request in run.requests:
        lines.append(
            (
                ("request        ", "label"),
                (f"{request.method} {request.url} -> 200 (fixture)", "text"),
            )
        )
    lines.append(
        (
            ("fetch_jobs     ", "label"),
            (
                f"{demo.adapter_class_name} -> {len(run.jobs)} jobs "
                f"(timeout_seconds={TIMEOUT_SECONDS}, max_jobs={MAX_JOBS})",
                "text",
            ),
        )
    )
    lines.append(
        (("#".rjust(index_width) + "  ", "comment"), *cells(headers, ("comment",) * 4)),
    )
    for number, (row, job) in enumerate(zip(rows, run.jobs, strict=True), start=1):
        lines.append(
            (
                (f"{number:>{index_width}}  ", "comment"),
                *cells(row, ("strong", "text", "text", row[3])),
            )
        )
        lines.append(((" " * (index_width + 2) + job.url, "url"),))
    lines.append(
        (("# REMOTE = is_remote_location(location), the GET /jobs?remote=true rule", "comment"),)
    )
    return lines


def plain_text(lines: Sequence[Line]) -> str:
    """Join styled transcript lines into the plain ``--dry-run`` output."""

    return "\n".join("".join(text for text, _ in line) for line in lines)


def _load_mono_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the first available monospace font, else Pillow's default font."""

    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    print("warning: no monospace font found; using Pillow's default font", file=sys.stderr)
    return ImageFont.load_default(size=size)


def _render_frame(
    lines: Sequence[Line],
    title: str,
    size: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    cursor: bool,
) -> Image.Image:
    """Draw one terminal-window frame showing ``lines``.

    Args:
        lines: Transcript lines visible in this frame.
        title: Window title.
        size: Canvas ``(width, height)`` in pixels.
        font: Monospace font.
        cursor: Whether to draw an idle prompt with a block cursor below the lines.

    Returns:
        RGB frame.
    """

    width, height = size
    image = Image.new("RGB", size, BASE_COLOR)
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # crisp terminal text with an exact, tiny palette
    left, top = WINDOW_MARGIN, WINDOW_MARGIN
    right, bottom = width - WINDOW_MARGIN, height - WINDOW_MARGIN
    bar_bottom = top + TITLE_BAR_HEIGHT
    draw.rounded_rectangle((left, top, right, bottom), radius=10, fill=PANEL_COLOR)
    draw.rounded_rectangle((left, top, right, bar_bottom), radius=10, fill=TITLE_BAR_COLOR)
    draw.rectangle((left, bar_bottom - 10, right, bar_bottom), fill=TITLE_BAR_COLOR)
    for i, color in enumerate(TRAFFIC_LIGHTS):
        cx, cy = left + 20 + i * 20, top + TITLE_BAR_HEIGHT // 2
        draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=color)
    title_x = (width - draw.textlength(title, font=font)) / 2
    draw.text(
        (title_x, top + TITLE_BAR_HEIGHT / 2), title, fill=TEXT_SECONDARY, font=font, anchor="lm"
    )

    x0 = left + TEXT_PADDING
    y = bar_bottom + TEXT_PADDING + FONT_SIZE
    for line in lines:
        x = float(x0)
        for text, style in line:
            draw.text((x, y), text, fill=STYLE_COLORS[style], font=font, anchor="ls")
            x += draw.textlength(text, font=font)
        y += LINE_HEIGHT
    if cursor:
        prompt_width = draw.textlength("$ ", font=font)
        draw.text((x0, y), "$ ", fill=PROMPT_COLOR, font=font, anchor="ls")
        cursor_left = x0 + prompt_width
        draw.rectangle((cursor_left, y - FONT_SIZE, cursor_left + 7, y + 2), fill=TEXT_PRIMARY)
    return image


def _terminal_palette() -> Image.Image:
    """Return a GIF palette holding exactly the colors the frames are drawn with.

    Text is drawn without anti-aliasing, so frames only contain these colors and
    every frame maps onto them losslessly (and compresses well).

    Returns:
        A ``P`` mode image carrying the palette.
    """

    colors = [BASE_COLOR, PANEL_COLOR, TITLE_BAR_COLOR, *TRAFFIC_LIGHTS, TEXT_PRIMARY]
    colors += [color for color in STYLE_COLORS.values() if color not in colors]
    palette = Image.new("P", (1, 1))
    palette.putpalette([channel for color in colors for channel in color])
    return palette


def render_gif(run: DemoRun, output_path: Path) -> tuple[int, int]:
    """Render the transcript of ``run`` as a looping terminal GIF.

    The frames reveal the command, the source config, the replayed request and
    finally the returned jobs; all frames share one exact palette.

    Args:
        run: Replayed demo run.
        output_path: Destination GIF path.

    Returns:
        ``(width, height)`` of the written GIF.
    """

    lines = transcript(run)
    font = _load_mono_font(FONT_SIZE)
    title = f"agentic-career-search: {run.demo.display_name} adapter ({FIXTURE_LABEL})"
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    text_width = max(
        probe.textlength(title, font=font) + 120,
        *(probe.textlength("".join(text for text, _ in line), font=font) for line in lines),
    )
    width = max(CANVAS_WIDTH, 2 * (WINDOW_MARGIN + TEXT_PADDING) + math.ceil(text_width))
    rows = len(lines) + 1  # the idle prompt below the transcript
    height = max(
        MIN_CANVAS_HEIGHT,
        2 * WINDOW_MARGIN + TITLE_BAR_HEIGHT + 2 * TEXT_PADDING + rows * LINE_HEIGHT,
    )
    config_end = 4
    request_end = config_end + 1 + len(run.requests) + 1
    reveal = (1, config_end, request_end, len(lines))
    frames_rgb = [
        _render_frame(lines[:count], title, (width, height), font, cursor=count == len(lines))
        for count in reveal
    ]
    palette = _terminal_palette()
    first, *rest = [
        frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames_rgb
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    first.save(
        output_path,
        save_all=True,
        append_images=rest,
        duration=list(FRAME_DURATIONS_MS),
        loop=0,
        optimize=True,
    )
    return width, height


def main(argv: Sequence[str] | None = None) -> int:
    """Replay the selected adapters and print or (re)write their demo GIFs.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slugs", nargs="*", help="demo slugs to render (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="print transcripts, write nothing")
    parser.add_argument("--list", action="store_true", help="list the slugs rendered by default")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEMO_DIR,
        help="where to write GIFs (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(SOURCE_DEMOS))
        return 0
    for slug in args.slugs or SOURCE_DEMOS:
        try:
            run = run_demo(resolve_demo(slug))
        except DemoError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            print(plain_text(transcript(run)))
            continue
        output_path = args.output_dir.resolve() / f"{slug}-source.gif"
        width, height = render_gif(run, output_path)
        shown = (
            output_path.relative_to(REPO_ROOT)
            if output_path.is_relative_to(REPO_ROOT)
            else output_path
        )
        size_bytes = output_path.stat().st_size
        print(f"wrote {shown} ({width}x{height}, {size_bytes:,} B, {len(run.jobs)} jobs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
