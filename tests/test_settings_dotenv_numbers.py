"""Digit-only .env values reach every text setting as the text the operator wrote.

lib_layered_config's dotenv and environment layers turn an unquoted value into an int whenever that
number reads back as the same text (``123456`` stays ``123456``). A text setting must therefore
accept such a number and keep its digits; otherwise a perfectly ordinary ``.env`` line such as
``EMAIL__SMTP_PASSWORD=123456`` stops the command with ``Input should be a valid string``.

These tests load a real ``.env`` through the real loader, so a change in the library's coercion
shows up here rather than on a user's machine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from pydantic import ValidationError

from vnc_remote_control.adapters.config.loader import get_config
from vnc_remote_control.adapters.config.vnc import build_rfb_timings
from vnc_remote_control.adapters.email.config import EmailConfig, load_email_config_from_dict
from vnc_remote_control.adapters.logging.setup import LoggingConfigModel

if TYPE_CHECKING:
    from pathlib import Path

    from lib_layered_config import Config


def _load_dotenv(tmp_path: Path, *lines: str) -> Config:
    dotenv = tmp_path / ".env"
    dotenv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return get_config(dotenv_path=str(dotenv))


def _section(config: Config, name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", config.get(name, default={}))


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    ("env_key", "attr", "raw"),
    [
        ("EMAIL__SMTP_PASSWORD", "smtp_password", "123456"),
        ("EMAIL__SMTP_USERNAME", "smtp_username", "1001"),
    ],
    ids=["smtp_password", "smtp_username"],
)
def test_digit_only_dotenv_value_reaches_an_email_text_setting_as_its_text(
    tmp_path: Path, clear_config_cache: None, env_key: str, attr: str, raw: str
) -> None:
    config = _load_dotenv(tmp_path, f"{env_key}={raw}")
    # Premise: the library hands the value over as a number. Without it the test proves nothing.
    assert isinstance(_section(config, "email")[attr], int)

    email = load_email_config_from_dict(config.as_dict())

    assert getattr(email, attr) == raw


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    ("env_key", "attr"),
    [("LIB_LOG_RICH__SERVICE", "service"), ("LIB_LOG_RICH__ENVIRONMENT", "environment")],
    ids=["service", "environment"],
)
def test_digit_only_dotenv_value_reaches_a_logging_text_setting_as_its_text(
    tmp_path: Path, clear_config_cache: None, env_key: str, attr: str
) -> None:
    loaded = _section(_load_dotenv(tmp_path, f"{env_key}=4711"), "lib_log_rich")
    assert isinstance(loaded[attr], int)

    assert getattr(LoggingConfigModel.model_validate(loaded), attr) == "4711"


@pytest.mark.os_agnostic
def test_a_numeric_setting_still_reads_as_a_number(tmp_path: Path, clear_config_cache: None) -> None:
    config = _load_dotenv(tmp_path, "EMAIL__TIMEOUT=45", "VNC__CLICK_HOLD=2")

    assert load_email_config_from_dict(config.as_dict()).timeout == 45.0
    assert build_rfb_timings(config).click_hold == 2.0


@pytest.mark.os_agnostic
def test_an_invalid_email_setting_is_still_refused(tmp_path: Path, clear_config_cache: None) -> None:
    config = _load_dotenv(tmp_path, "EMAIL__TIMEOUT=-5")

    with pytest.raises(ValidationError, match="timeout must be positive"):
        EmailConfig.model_validate(_section(config, "email"))
