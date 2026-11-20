"""Parse the ``[vnc]`` configuration section into RFB event timings.

Reads the per-event delays from layered configuration and validates them at the
boundary with Pydantic, then maps them onto the domain :class:`RfbTimings` value
object. Unspecified keys fall back to the tuned defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ...domain.errors import ConfigurationError
from ...domain.timing import RfbTimings

if TYPE_CHECKING:
    from lib_layered_config import Config

_DEFAULTS = RfbTimings()


class VncConfigModel(BaseModel):
    """Validated ``[vnc]`` timing settings (seconds, each must be positive)."""

    model_config = ConfigDict(extra="ignore")

    key_down_hold: float = Field(default=_DEFAULTS.key_down_hold, gt=0)
    key_up_gap: float = Field(default=_DEFAULTS.key_up_gap, gt=0)
    click_move_gap: float = Field(default=_DEFAULTS.click_move_gap, gt=0)
    click_hold: float = Field(default=_DEFAULTS.click_hold, gt=0)
    click_release_gap: float = Field(default=_DEFAULTS.click_release_gap, gt=0)


class InvalidVncConfigError(ConfigurationError):
    """The ``[vnc]`` section holds a value the timings refuse: one ``vnc.<key>: <reason>`` per problem.

    A line names the key and pydantic's reason and never repeats the refused value, so the CLI
    can print it as is, one ``Error:`` line each, like the other configuration sections.

    Attributes:
        problems: One line per refused setting.

    Example:
        >>> try:
        ...     VncConfigModel.model_validate({"key_up_gap": -1})
        ... except ValidationError as exc:
        ...     print(InvalidVncConfigError.from_validation_error(exc))
        vnc.key_up_gap: Input should be greater than 0
    """

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems

    @classmethod
    def from_validation_error(cls, error: ValidationError) -> InvalidVncConfigError:
        """Build the refusal from pydantic's error, one line per problem, without the input.

        Args:
            error: The error validating the ``[vnc]`` section raised.

        Returns:
            The refusal naming each key; a problem with the whole section reads ``vnc: <reason>``.
        """
        lines = [
            f"{'.'.join(('vnc', *map(str, item['loc'])))}: {item['msg']}"
            for item in error.errors(include_url=False, include_input=False)
        ]
        return cls(lines)


def build_rfb_timings(config: Config) -> RfbTimings:
    """Build :class:`RfbTimings` from the ``[vnc]`` section of ``config``.

    Args:
        config: Already-loaded layered configuration object.

    Returns:
        The configured event timings, or the tuned defaults when the section is
        absent or empty.

    Raises:
        InvalidVncConfigError: A value in the section is not a positive number.
    """
    raw: object = config.get("vnc", default={})
    try:
        parsed = VncConfigModel.model_validate(cast("dict[str, object]", raw) if raw else {})
    except ValidationError as exc:
        raise InvalidVncConfigError.from_validation_error(exc) from None
    return RfbTimings(
        key_down_hold=parsed.key_down_hold,
        key_up_gap=parsed.key_up_gap,
        click_move_gap=parsed.click_move_gap,
        click_hold=parsed.click_hold,
        click_release_gap=parsed.click_release_gap,
    )


__all__ = ["InvalidVncConfigError", "VncConfigModel", "build_rfb_timings"]
