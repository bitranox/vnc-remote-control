"""The limits btx_lib_mail applies to every send, reached through this app's send_email.

The app passes no recipient or attachment count and no extension list of its own unless
``[email.attachments]`` names one, so the library's defaults decide. These tests pin what
those defaults do end to end: a btx_lib_mail release that changes them fails here instead of
changing what a user's send-email accepts without a word.
"""

from __future__ import annotations

from typing import IO, TYPE_CHECKING

import pytest
from btx_lib_mail.lib_mail import AttachmentSecurityError

from vnc_remote_control.adapters.email.sender import EmailConfig, load_email_config_from_dict, send_email

if TYPE_CHECKING:
    from pathlib import Path

    from btx_lib_mail.lib_mail import DeliveryOptions

#: The library's default caps on one send.
_RECIPIENT_MAX_COUNT = 1000
_ATTACHMENT_MAX_COUNT = 100
_LIBRARY_DEFAULT_MAX_SIZE_BYTES = 26_214_400


class _CountingTransport:
    """Delivery seam that counts deliveries instead of sending."""

    def __init__(self) -> None:
        self.deliveries = 0

    def deliver(
        self,
        *,
        host: str,
        sender: str,
        recipient: str,
        message: IO[bytes],
        delivery: DeliveryOptions,
    ) -> None:
        """Count the delivery."""
        del host, sender, recipient, message, delivery
        self.deliveries += 1


def _config() -> EmailConfig:
    # The blocked directories are emptied so the temporary directory a test writes its
    # attachments to is never what refuses them; the extension defaults stay the library's.
    return EmailConfig(
        smtp_hosts=["smtp.test.com:587"],
        from_address="sender@test.com",
        attachment_blocked_directories=frozenset(),
    )


@pytest.mark.os_agnostic
@pytest.mark.parametrize("name", ["setup.exe", "run.bat", "install.sh", "tool.py"])
def test_the_default_blocked_extensions_hold_both_lists_on_every_platform(tmp_path: Path, name: str) -> None:
    """A Windows executable and a POSIX script are both refused, whatever the platform."""
    attachment = tmp_path / name
    attachment.write_text("payload")
    transport = _CountingTransport()

    with pytest.raises(AttachmentSecurityError):
        send_email(
            config=_config(),
            recipients="to@test.com",
            subject="s",
            attachments=[attachment],
            transport=transport,
        )

    assert transport.deliveries == 0


@pytest.mark.os_agnostic
def test_more_recipients_than_the_library_allows_are_refused_before_any_delivery() -> None:
    """One send to more than 1000 distinct recipients is a ValueError and delivers nothing."""
    recipients = [f"user{index}@test.com" for index in range(_RECIPIENT_MAX_COUNT + 1)]
    transport = _CountingTransport()

    with pytest.raises(ValueError, match="recipient"):
        send_email(config=_config(), recipients=recipients, subject="s", transport=transport)

    assert transport.deliveries == 0


@pytest.mark.os_agnostic
def test_the_recipient_limit_itself_is_accepted() -> None:
    """Exactly 1000 recipients are delivered, one message each."""
    recipients = [f"user{index}@test.com" for index in range(_RECIPIENT_MAX_COUNT)]
    transport = _CountingTransport()

    assert send_email(config=_config(), recipients=recipients, subject="s", transport=transport) is True
    assert transport.deliveries == _RECIPIENT_MAX_COUNT


@pytest.mark.os_agnostic
def test_more_attachments_than_the_library_allows_are_refused_before_any_delivery(tmp_path: Path) -> None:
    """One send with more than 100 attachments is a ValueError and delivers nothing."""
    attachments: list[Path] = []
    for index in range(_ATTACHMENT_MAX_COUNT + 1):
        path = tmp_path / f"part{index}.txt"
        path.write_text("x")
        attachments.append(path)
    transport = _CountingTransport()

    with pytest.raises(ValueError, match="attachment"):
        send_email(
            config=_config(),
            recipients="to@test.com",
            subject="s",
            attachments=attachments,
            transport=transport,
        )

    assert transport.deliveries == 0


@pytest.mark.os_agnostic
def test_a_size_limit_of_zero_lifts_the_library_default(tmp_path: Path) -> None:
    """``[email.attachments] max_size_bytes = 0`` disables the size check, as the shipped file says.

    ``send()`` reads a size limit of None as "use the configured default" (25 MiB), so the
    lifted limit has to reach the library as a setting rather than as a missing keyword.
    """
    config = load_email_config_from_dict(
        {
            "email": {
                "smtp_hosts": ["smtp.test.com:587"],
                "from_address": "sender@test.com",
                "attachments": {"max_size_bytes": 0, "blocked_directories": ["/nonexistent-blocked-dir"]},
            }
        }
    )
    attachment = tmp_path / "large.txt"
    with attachment.open("wb") as handle:
        # Sparse where the file system allows it: the size is what the check reads.
        handle.truncate(_LIBRARY_DEFAULT_MAX_SIZE_BYTES + 1)
    transport = _CountingTransport()

    assert config.attachment_max_size_bytes is None
    assert (
        send_email(config=config, recipients="to@test.com", subject="s", attachments=[attachment], transport=transport)
        is True
    )
    assert transport.deliveries == 1


@pytest.mark.os_agnostic
def test_a_configured_size_limit_still_refuses_a_larger_attachment(tmp_path: Path) -> None:
    """Control: the same send with a limit below the file size is refused."""
    config = load_email_config_from_dict(
        {
            "email": {
                "smtp_hosts": ["smtp.test.com:587"],
                "from_address": "sender@test.com",
                "attachments": {"max_size_bytes": 10, "blocked_directories": ["/nonexistent-blocked-dir"]},
            }
        }
    )
    attachment = tmp_path / "small.txt"
    attachment.write_text("more than ten bytes")
    transport = _CountingTransport()

    with pytest.raises(AttachmentSecurityError):
        send_email(config=config, recipients="to@test.com", subject="s", attachments=[attachment], transport=transport)

    assert transport.deliveries == 0
