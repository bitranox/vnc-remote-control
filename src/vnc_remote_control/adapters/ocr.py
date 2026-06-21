"""OCR word extraction from tesseract TSV output, pure logic.

The OCR-driven subcommands (``ocr``, ``click-text``) run tesseract in TSV mode
and parse the result here. A recognized word carries its bounding box, and the
click point is the box center. Keeping the parser separate from the subprocess
call makes it testable without tesseract or a live server.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass

#: Words below this confidence are dropped as noise.
DEFAULT_MIN_CONFIDENCE = 40.0

#: Shared message for when the required tesseract binary is not installed.
TESSERACT_REQUIRED_MSG = (
    "tesseract is required for OCR; install tesseract-ocr "
    "(Debian/Ubuntu: sudo apt-get install tesseract-ocr, macOS: brew install tesseract, "
    "Windows: choco install tesseract)"
)

#: Column names in tesseract's TSV header (used to locate fields by name).
_TSV_COLUMNS = (
    "level",
    "page_num",
    "block_num",
    "par_num",
    "line_num",
    "word_num",
    "left",
    "top",
    "width",
    "height",
    "conf",
    "text",
)


@dataclass(frozen=True)
class Word:
    """One recognized word with its bounding box and confidence.

    ``center`` is the click point: the middle of the bounding box, in absolute
    framebuffer pixels.
    """

    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float

    @property
    def cx(self) -> int:
        """X coordinate of the box center."""
        return self.left + self.width // 2

    @property
    def cy(self) -> int:
        """Y coordinate of the box center."""
        return self.top + self.height // 2

    def format_line(self) -> str:
        """Render the stable, parseable one-line form used by the ``ocr`` output.

        >>> Word("OK", 10, 20, 30, 40, 95.0).format_line()
        '25 40 30x40 conf=95 OK'
        """
        return f"{self.cx} {self.cy} {self.width}x{self.height} conf={round(self.conf)} {self.text}"


def parse_tsv(tsv: str, min_confidence: float = DEFAULT_MIN_CONFIDENCE) -> list[Word]:
    """Parse tesseract TSV text into a list of confident, non-empty words.

    Rows with empty text, a non-numeric confidence, or confidence at or below
    ``min_confidence`` are skipped. Field order is resolved from the header line
    rather than assumed, so it survives tesseract column changes.

    >>> sample = "left\\ttop\\twidth\\theight\\tconf\\ttext\\n10\\t20\\t30\\t40\\t95\\tOK\\n"
    >>> words = parse_tsv(sample)
    >>> (words[0].text, words[0].cx, words[0].cy)
    ('OK', 25, 40)
    """
    lines = tsv.splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    index = {name: header.index(name) for name in _TSV_COLUMNS if name in header}
    required = ("left", "top", "width", "height", "conf", "text")
    if not all(name in index for name in required):
        return []

    words: list[Word] = []
    for raw in lines[1:]:
        fields = raw.split("\t")
        if len(fields) <= index["text"]:
            continue
        text = fields[index["text"]].strip()
        if not text:
            continue
        try:
            conf = float(fields[index["conf"]])
            left = int(fields[index["left"]])
            top = int(fields[index["top"]])
            width = int(fields[index["width"]])
            height = int(fields[index["height"]])
        except ValueError:
            continue
        if conf <= min_confidence:
            continue
        words.append(Word(text=text, left=left, top=top, width=width, height=height, conf=conf))
    return words


def filter_words(words: list[Word], pattern: str) -> list[Word]:
    """Return words whose text matches ``pattern`` (case-insensitive).

    The pattern is tried as a regular expression first; if it is not valid
    regex, it falls back to a case-insensitive substring test.

    >>> ws = [Word("Start", 0, 0, 10, 10, 90.0), Word("Cancel", 0, 0, 10, 10, 90.0)]
    >>> [w.text for w in filter_words(ws, "can")]
    ['Cancel']
    """
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        needle = pattern.lower()
        return [w for w in words if needle in w.text.lower()]
    return [w for w in words if rx.search(w.text)]


def first_match(words: list[Word], pattern: str) -> Word | None:
    """Return the first word matching ``pattern``, or ``None`` if none match.

    >>> ws = [Word("Start", 0, 0, 10, 10, 90.0), Word("Cancel", 0, 0, 10, 10, 90.0)]
    >>> first_match(ws, "cancel").text
    'Cancel'
    >>> first_match(ws, "nope") is None
    True
    """
    matches = filter_words(words, pattern)
    return matches[0] if matches else None


def tesseract_available() -> bool:
    """Return whether the required tesseract binary is on PATH.

    >>> isinstance(tesseract_available(), bool)
    True
    """
    return shutil.which("tesseract") is not None


def run_tesseract_tsv(png_path: str) -> str | None:
    """Run tesseract on ``png_path`` in sparse-text TSV mode.

    Returns the TSV text, or ``None`` if tesseract is missing or the run failed.
    Callers that need a clear "tesseract is required" error should check
    :func:`tesseract_available` first.
    """
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603 B607
            ["tesseract", png_path, "stdout", "--psm", "11", "tsv"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout
