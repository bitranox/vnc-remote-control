"""Timing value object for RFB key and pointer events.

The delays (in seconds) between the down and up edges of each event. The defaults
match values tuned so guests register every event; a sluggish guest (an old
desktop, a loaded VM) may drop events typed too fast, so the delays are tunable
through the ``[vnc]`` config section and scaled by the ``--delay-scale`` CLI
option.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Default hold between a key-down and key-up edge.
DEFAULT_KEY_DOWN_HOLD = 0.05
#: Default gap after a key-up edge before the next key.
DEFAULT_KEY_UP_GAP = 0.09
#: Default gap after moving the pointer before pressing the button.
DEFAULT_CLICK_MOVE_GAP = 0.1
#: Default hold between a button-down and button-up edge.
DEFAULT_CLICK_HOLD = 0.12
#: Default gap after releasing the button.
DEFAULT_CLICK_RELEASE_GAP = 0.2


@dataclass(frozen=True)
class RfbTimings:
    """Delays (seconds) between the down and up edges of RFB events."""

    key_down_hold: float = DEFAULT_KEY_DOWN_HOLD
    key_up_gap: float = DEFAULT_KEY_UP_GAP
    click_move_gap: float = DEFAULT_CLICK_MOVE_GAP
    click_hold: float = DEFAULT_CLICK_HOLD
    click_release_gap: float = DEFAULT_CLICK_RELEASE_GAP

    def scaled(self, factor: float) -> RfbTimings:
        """Return a copy with every delay multiplied by ``factor``.

        >>> RfbTimings().scaled(2.0).key_down_hold
        0.1
        >>> RfbTimings().scaled(1.0) == RfbTimings()
        True
        """
        return RfbTimings(
            key_down_hold=self.key_down_hold * factor,
            key_up_gap=self.key_up_gap * factor,
            click_move_gap=self.click_move_gap * factor,
            click_hold=self.click_hold * factor,
            click_release_gap=self.click_release_gap * factor,
        )


__all__ = [
    "DEFAULT_CLICK_HOLD",
    "DEFAULT_CLICK_MOVE_GAP",
    "DEFAULT_CLICK_RELEASE_GAP",
    "DEFAULT_KEY_DOWN_HOLD",
    "DEFAULT_KEY_UP_GAP",
    "RfbTimings",
]
