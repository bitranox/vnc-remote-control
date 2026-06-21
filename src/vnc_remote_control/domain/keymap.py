"""Keysym constants for a VNC/RFB server.

This client behaves like a standard VNC client and sends LITERAL keysyms: a
character's keysym is its Unicode code point. The RFB server maps each KeyEvent
keysym to the guest's configured keyboard layout server-side. A layout-aware
server such as openvmm does this for arbitrary characters and any layout (its
--vnc-keyboard-layout flag selects it; on Proxmox the ovm shim derives it from
the VM's ``keyboard:`` key). There is no client-side reverse map, no AltGr
juggling, and nothing is untypeable.

This module holds the named-key table and the one literal mapping helper. It does
no socket I/O.
"""

from __future__ import annotations

#: X11 keysym for the Return key.
RETURN = 0xFF0D
#: X11 keysym for the Backspace key.
BACKSPACE = 0xFF08

#: Named keys addressable by the ``key`` subcommand. Values are X11 keysyms.
NAMED_KEYS: dict[str, int] = {
    "enter": RETURN,
    "return": RETURN,
    "backspace": BACKSPACE,
    "tab": 0xFF09,
    "esc": 0xFF1B,
    "escape": 0xFF1B,
    "space": 0x0020,
    "delete": 0xFFFF,
    "del": 0xFFFF,
    "home": 0xFF50,
    "end": 0xFF57,
    "pageup": 0xFF55,
    "pagedown": 0xFF56,
    "up": 0xFF52,
    "down": 0xFF54,
    "left": 0xFF51,
    "right": 0xFF53,
    "f1": 0xFFBE,
    "f2": 0xFFBF,
    "f3": 0xFFC0,
    "f4": 0xFFC1,
    "f5": 0xFFC2,
    "f6": 0xFFC3,
    "f7": 0xFFC4,
    "f8": 0xFFC5,
    "f9": 0xFFC6,
    "f10": 0xFFC7,
    "f11": 0xFFC8,
    "f12": 0xFFC9,
}


def char_keysym(ch: str) -> int:
    """Return the literal keysym for ``ch``: its Unicode code point.

    The layout-aware server maps this keysym to the guest's keyboard layout, so
    no client-side translation is needed.

    >>> char_keysym("a") == ord("a")
    True
    >>> char_keysym(":") == ord(":")
    True
    >>> char_keysym("|") == ord("|")
    True
    """
    return ord(ch)
