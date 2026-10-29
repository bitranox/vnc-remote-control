"""Tests for the literal keysym helper and the named-key table."""

from __future__ import annotations

import string

import pytest

from vnc_remote_control.domain import keymap


@pytest.mark.os_agnostic
def test_char_keysym_is_the_code_point() -> None:
    """Every character maps to its own code point; nothing is special-cased."""
    for ch in string.ascii_letters + string.digits + ":/-_;@\\{}[]|~":
        assert keymap.char_keysym(ch) == ord(ch)


@pytest.mark.os_agnostic
def test_char_keysym_pipe_is_literal() -> None:
    """'|' maps to its literal keysym."""
    assert keymap.char_keysym("|") == ord("|")


@pytest.mark.os_agnostic
def test_named_keys_cover_common_keys() -> None:
    """The named-key table maps the keys the CLI advertises."""
    assert keymap.NAMED_KEYS["enter"] == keymap.RETURN
    assert keymap.NAMED_KEYS["backspace"] == keymap.BACKSPACE
    for name in ("tab", "esc", "up", "down", "left", "right", "f8"):
        assert name in keymap.NAMED_KEYS


@pytest.mark.os_agnostic
def test_needs_us_shift_covers_uppercase_and_shifted_symbols() -> None:
    """Every character on a shifted US key needs Shift; its unshifted twin does not."""
    for ch in string.ascii_uppercase + '~!@#$%^&*()_+{}|:"<>?':
        assert keymap.needs_us_shift(ch), ch
    for ch in string.ascii_lowercase + string.digits + r"`-=[]\;',./ ":
        assert not keymap.needs_us_shift(ch), ch


@pytest.mark.os_agnostic
def test_needs_us_shift_is_false_beyond_ascii() -> None:
    """A character with no US key gets no Shift; the server decides what it does."""
    assert not keymap.needs_us_shift("ä")
    assert not keymap.needs_us_shift("Ä")
