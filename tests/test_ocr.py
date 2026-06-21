"""Tests for tesseract TSV parsing and word matching."""

from __future__ import annotations

import pytest

from vnc_remote_control.adapters import ocr

# A small captured-style tesseract TSV sample. Header then word rows. The two
# level-5 rows with text are real words; the blank-text rows model the structure
# rows tesseract emits for page/block/line that carry conf=-1.
_TSV = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    "1\t1\t0\t0\t0\t0\t0\t0\t800\t600\t-1\t\n"
    "5\t1\t1\t1\t1\t1\t100\t200\t60\t20\t95\tStart\n"
    "5\t1\t1\t1\t1\t2\t300\t400\t80\t24\t88\tCancel\n"
    "5\t1\t1\t1\t2\t1\t500\t450\t40\t18\t12\tnoise\n"
)


@pytest.mark.os_agnostic
def test_parse_tsv_extracts_confident_words() -> None:
    """Only non-empty words above the confidence floor survive."""
    words = ocr.parse_tsv(_TSV)
    assert [w.text for w in words] == ["Start", "Cancel"]


@pytest.mark.os_agnostic
def test_parse_tsv_computes_box_centers() -> None:
    """Word centers are the middle of the bounding box."""
    words = ocr.parse_tsv(_TSV)
    start = words[0]
    assert (start.cx, start.cy) == (100 + 30, 200 + 10)
    cancel = words[1]
    assert (cancel.cx, cancel.cy) == (300 + 40, 400 + 12)


@pytest.mark.os_agnostic
def test_parse_tsv_honors_min_confidence() -> None:
    """Raising the floor drops lower-confidence words."""
    words = ocr.parse_tsv(_TSV, min_confidence=90.0)
    assert [w.text for w in words] == ["Start"]


@pytest.mark.os_agnostic
def test_parse_tsv_empty_input_is_empty() -> None:
    """Empty or headerless input yields no words."""
    assert ocr.parse_tsv("") == []
    assert ocr.parse_tsv("not\ta\theader\n") == []


@pytest.mark.os_agnostic
def test_format_line_is_stable() -> None:
    """The ocr output line format is the documented shape."""
    word = ocr.Word("OK", 10, 20, 30, 40, 95.0)
    assert word.format_line() == "25 40 30x40 conf=95 OK"


@pytest.mark.os_agnostic
def test_filter_words_substring_case_insensitive() -> None:
    """A plain substring matches case-insensitively."""
    words = ocr.parse_tsv(_TSV)
    assert [w.text for w in ocr.filter_words(words, "can")] == ["Cancel"]


@pytest.mark.os_agnostic
def test_filter_words_regex() -> None:
    """A regex pattern filters by match."""
    words = ocr.parse_tsv(_TSV)
    assert [w.text for w in ocr.filter_words(words, "^Star")] == ["Start"]


@pytest.mark.os_agnostic
def test_first_match_returns_first_or_none() -> None:
    """first_match returns the first matching word or None."""
    words = ocr.parse_tsv(_TSV)
    match = ocr.first_match(words, "cancel")
    assert match is not None
    assert match.text == "Cancel"
    assert ocr.first_match(words, "missing") is None


@pytest.mark.os_agnostic
def test_tesseract_available_reflects_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """tesseract_available is True only when the binary is on PATH."""

    def found(_name: str) -> str | None:
        return "/usr/bin/tesseract"

    def missing(_name: str) -> str | None:
        return None

    monkeypatch.setattr(ocr.shutil, "which", found)
    assert ocr.tesseract_available() is True
    monkeypatch.setattr(ocr.shutil, "which", missing)
    assert ocr.tesseract_available() is False


@pytest.mark.os_agnostic
def test_required_message_names_the_install_command() -> None:
    """The shared required-message states tesseract is required and how to install it."""
    msg = ocr.TESSERACT_REQUIRED_MSG
    assert "tesseract is required" in msg
    assert "tesseract-ocr" in msg
