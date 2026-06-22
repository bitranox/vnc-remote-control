"""Parse the ``[vnc]`` configuration section into RFB event timings.

Reads the per-event delays from layered configuration and validates them at the
boundary with Pydantic, then maps them onto the domain :class:`RfbTimings` value
object. Unspecified keys fall back to the tuned defaults.
"""

from __future__ import annotations

from typing import cast

from lib_layered_config import Config
from pydantic import BaseModel, ConfigDict, Field

from ...domain.timing import RfbTimings

_DEFAULTS = RfbTimings()


class VncConfigModel(BaseModel):
    """Validated ``[vnc]`` timing settings (seconds, each must be positive)."""

    model_config = ConfigDict(extra="ignore")

    key_down_hold: float = Field(default=_DEFAULTS.key_down_hold, gt=0)
    key_up_gap: float = Field(default=_DEFAULTS.key_up_gap, gt=0)
    click_move_gap: float = Field(default=_DEFAULTS.click_move_gap, gt=0)
    click_hold: float = Field(default=_DEFAULTS.click_hold, gt=0)
    click_release_gap: float = Field(default=_DEFAULTS.click_release_gap, gt=0)


def build_rfb_timings(config: Config) -> RfbTimings:
    """Build :class:`RfbTimings` from the ``[vnc]`` section of ``config``.

    Args:
        config: Already-loaded layered configuration object.

    Returns:
        The configured event timings, or the tuned defaults when the section is
        absent or empty.
    """
    raw: object = config.get("vnc", default={})
    parsed = VncConfigModel.model_validate(cast("dict[str, object]", raw) if raw else {})
    return RfbTimings(
        key_down_hold=parsed.key_down_hold,
        key_up_gap=parsed.key_up_gap,
        click_move_gap=parsed.click_move_gap,
        click_hold=parsed.click_hold,
        click_release_gap=parsed.click_release_gap,
    )


__all__ = ["VncConfigModel", "build_rfb_timings"]
