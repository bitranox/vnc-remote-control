"""Public package surface for vnc-remote-control.

Exposes the VNC/RFB client, OCR helpers, and keymap so the package can be used
as a library as well as a CLI, alongside the shared metadata and configuration
helpers from the application skeleton.
"""

from __future__ import annotations

# Metadata
from .__init__conf__ import print_info

# VNC/RFB adapter (the tool's core)
from .adapters.ocr import Word, first_match, parse_tsv
from .adapters.rfb import RfbClient, RfbError, draw_crosshair, draw_grid

# Composition exports (wired adapters)
from .composition import get_config

# Domain exports
from .domain.behaviors import (
    CANONICAL_GREETING,
    build_greeting,
)
from .domain.keymap import char_keysym
from .domain.timing import RfbTimings

__all__ = [
    "CANONICAL_GREETING",
    "RfbClient",
    "RfbError",
    "RfbTimings",
    "Word",
    "build_greeting",
    "char_keysym",
    "draw_crosshair",
    "draw_grid",
    "first_match",
    "get_config",
    "parse_tsv",
    "print_info",
]
