"""CLI command implementations.

Collects all subcommand functions and re-exports them for registration
with the root CLI group.

Contents:
    * Info commands from :mod:`.info`
    * Config commands from :mod:`.config`
    * Email commands from :mod:`.email` (subpackage)
    * Logging commands from :mod:`.logging`
"""

from __future__ import annotations

from .config import cli_config, cli_config_deploy, cli_config_generate_examples
from .email import cli_send_email, cli_send_notification
from .info import cli_fail, cli_hello, cli_info
from .logging import cli_logdemo
from .vnc import (
    cli_click,
    cli_click_text,
    cli_key,
    cli_ocr,
    cli_screenshot,
    cli_type,
)

__all__ = [
    "cli_click",
    "cli_click_text",
    "cli_config",
    "cli_config_deploy",
    "cli_config_generate_examples",
    "cli_fail",
    "cli_hello",
    "cli_info",
    "cli_key",
    "cli_logdemo",
    "cli_ocr",
    "cli_screenshot",
    "cli_send_email",
    "cli_send_notification",
    "cli_type",
]
