"""VNC/RFB remote-control subcommands.

The six commands this tool exists for: ``type``, ``key``, ``click``,
``screenshot``, ``ocr``, and ``click-text``. They drive a VNC/RFB server selected
by the global ``--host`` and ``--port`` options (read off the shared
:class:`CLIContext`). The OCR commands additionally require the tesseract binary,
a system dependency.

Keyboard model: the server owns the layout. A layout-aware server (such as
openvmm) maps each literal keysym to the guest's configured keyboard layout, so
``type`` sends literal keysyms and never compensates client-side.

Coordinate model: RFB PointerEvent coordinates are absolute framebuffer pixels,
the same pixels a native-resolution screenshot contains, so a coordinate read off
a screenshot is the exact click coordinate.
"""

from __future__ import annotations

import logging
import tempfile

import lib_log_rich.runtime
import rich_click as click

from ... import ocr
from ...rfb import RfbClient, RfbError
from ..constants import CLICK_CONTEXT_SETTINGS
from ..context import get_cli_context
from ..typed_click import argument, option

logger = logging.getLogger(__name__)

#: Number of comma-separated parts expected in an ``X,Y`` value.
_XY_PARTS = 2


def _server(ctx: click.Context) -> tuple[str, int, str | None]:
    """Return ``(host, port, password)`` from the CLI context, requiring ``--port``."""
    cli_ctx = get_cli_context(ctx)
    if cli_ctx.port is None:
        raise click.UsageError("--port is required for this command (e.g. --port 5901)")
    return cli_ctx.host, cli_ctx.port, cli_ctx.password


def _parse_xy(_ctx: click.Context, _param: click.Parameter, value: str | None) -> tuple[int, int] | None:
    """Parse an ``X,Y`` option value into a tuple of ints, for ``--mark``.

    Examples:
        >>> _parse_xy(None, None, None) is None
        True
        >>> _parse_xy(None, None, "12,34")
        (12, 34)
    """
    if value is None:
        return None
    parts = value.split(",")
    if len(parts) != _XY_PARTS:
        raise click.BadParameter("expected X,Y")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise click.BadParameter("X and Y must be integers") from exc


def _temp_png() -> str:
    """Return a fresh temp PNG path."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        return tmp.name


def _ocr_words(host: str, port: int, password: str | None, min_confidence: float) -> list[ocr.Word]:
    """Screenshot the framebuffer, OCR it, and return parsed words.

    Raises ``RfbError`` when the required tesseract binary is unavailable so the
    CLI boundary maps it to a clear nonzero exit.
    """
    if not ocr.tesseract_available():
        raise RfbError(ocr.TESSERACT_REQUIRED_MSG)
    png = _temp_png()
    with RfbClient(host, port, password=password) as client:
        client.screenshot(png)
    tsv = ocr.run_tesseract_tsv(png)
    if tsv is None:
        raise RfbError(f"{ocr.TESSERACT_REQUIRED_MSG} (tesseract run failed)")
    return ocr.parse_tsv(tsv, min_confidence=min_confidence)


@click.command("type", context_settings=CLICK_CONTEXT_SETTINGS)
@argument("text")
@option("--enter", is_flag=True, default=False, help="press Return after typing")
@click.pass_context
def cli_type(ctx: click.Context, text: str, *, enter: bool) -> None:
    """Type a literal string into the guest."""
    host, port, password = _server(ctx)
    with lib_log_rich.runtime.bind(job_id="cli-type", extra={"command": "type"}):
        logger.info("Typing text into guest")
        with RfbClient(host, port, password=password) as client:
            client.type_text(text)
            if enter:
                client.press("enter")
    click.echo("typed", err=True)


@click.command("key", context_settings=CLICK_CONTEXT_SETTINGS)
@argument("name")
@click.pass_context
def cli_key(ctx: click.Context, name: str) -> None:
    """Press a single named key such as enter, tab, or esc."""
    host, port, password = _server(ctx)
    with lib_log_rich.runtime.bind(job_id="cli-key", extra={"command": "key"}):
        logger.info("Pressing named key")
        with RfbClient(host, port, password=password) as client:
            client.press(name)
    click.echo(f"pressed {name}", err=True)


@click.command("click", context_settings=CLICK_CONTEXT_SETTINGS)
@argument("x", type=int)
@argument("y", type=int)
@click.pass_context
def cli_click(ctx: click.Context, x: int, y: int) -> None:
    """Left-click at pixel position X Y."""
    host, port, password = _server(ctx)
    with lib_log_rich.runtime.bind(job_id="cli-click", extra={"command": "click"}):
        logger.info("Clicking at pixel position")
        with RfbClient(host, port, password=password) as client:
            client.click(x, y)
    click.echo(f"clicked ({x}, {y})", err=True)


@click.command("screenshot", context_settings=CLICK_CONTEXT_SETTINGS)
@argument("outfile")
@option(
    "--mark",
    callback=_parse_xy,
    metavar="X,Y",
    default=None,
    help="draw a crosshair through pixel X,Y to confirm a click coordinate",
)
@option("--grid", type=int, metavar="N", default=None, help="draw faint gridlines every N pixels")
@click.pass_context
def cli_screenshot(ctx: click.Context, outfile: str, mark: tuple[int, int] | None, grid: int | None) -> None:
    """Save the native-resolution framebuffer to a PNG file."""
    host, port, password = _server(ctx)
    with lib_log_rich.runtime.bind(job_id="cli-screenshot", extra={"command": "screenshot"}):
        logger.info("Capturing framebuffer screenshot")
        with RfbClient(host, port, password=password) as client:
            width, height = client.screenshot(outfile, mark=mark, grid=grid)
    # Parseable resolution line on stdout so an LLM can read the native size and
    # trust that screenshot pixels equal click coordinates.
    click.echo(f"resolution: {width}x{height}")
    click.echo(f"wrote {outfile} ({width}x{height})", err=True)


@click.command("ocr", context_settings=CLICK_CONTEXT_SETTINGS)
@option(
    "--grep",
    metavar="PATTERN",
    default=None,
    help="only list words whose text matches PATTERN (case-insensitive regex or substring)",
)
@option(
    "--min-confidence",
    type=float,
    default=ocr.DEFAULT_MIN_CONFIDENCE,
    show_default=True,
    metavar="N",
    help="drop words with confidence at or below N",
)
@click.pass_context
def cli_ocr(ctx: click.Context, grep: str | None, min_confidence: float) -> None:
    """OCR the screen and list recognized words with click centers (requires tesseract)."""
    host, port, password = _server(ctx)
    with lib_log_rich.runtime.bind(job_id="cli-ocr", extra={"command": "ocr"}):
        logger.info("Running OCR over the screen")
        words = _ocr_words(host, port, password, min_confidence)
    if grep is not None:
        words = ocr.filter_words(words, grep)
    for word in words:
        click.echo(word.format_line())


@click.command("click-text", context_settings=CLICK_CONTEXT_SETTINGS)
@argument("pattern")
@option(
    "--min-confidence",
    type=float,
    default=ocr.DEFAULT_MIN_CONFIDENCE,
    show_default=True,
    metavar="N",
    help="drop words with confidence at or below N",
)
@click.pass_context
def cli_click_text(ctx: click.Context, pattern: str, min_confidence: float) -> None:
    """OCR the screen and click the first word matching a pattern (requires tesseract)."""
    host, port, password = _server(ctx)
    with lib_log_rich.runtime.bind(job_id="cli-click-text", extra={"command": "click-text"}):
        logger.info("Clicking on-screen text by pattern")
        words = _ocr_words(host, port, password, min_confidence)
        target = ocr.first_match(words, pattern)
        if target is None:
            click.echo(f"no on-screen text matched {pattern!r}", err=True)
            raise SystemExit(1)
        with RfbClient(host, port, password=password) as client:
            client.click(target.cx, target.cy)
    click.echo(f'clicked "{target.text}" at ({target.cx},{target.cy})')


__all__ = [
    "cli_click",
    "cli_click_text",
    "cli_key",
    "cli_ocr",
    "cli_screenshot",
    "cli_type",
]
