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
