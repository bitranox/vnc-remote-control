"""CLI stories for the VNC subcommands (no live VNC server needed)."""

from __future__ import annotations

import pytest

from vnc_remote_control.adapters import cli as cli_mod
from vnc_remote_control.adapters import ocr
from vnc_remote_control.adapters.cli.commands import vnc as vnc_cmd
from vnc_remote_control.composition import build_production


class _FakeClient:
    """A stand-in RfbClient that records clicks and fakes a screenshot."""

    last_click: tuple[int, int] | None = None

    def __init__(self, host: str, port: int, password: str | None = None) -> None:
        self.host = host
        self.port = port
        self.password = password

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def screenshot(
        self,
        out_path: str,
        mark: tuple[int, int] | None = None,
        grid: int | None = None,
    ) -> tuple[int, int]:
        return 1024, 768

    def click(self, x: int, y: int) -> None:
        type(self).last_click = (x, y)


def _two_words(_host: str, _port: int, _password: str | None, _min_confidence: float) -> list[ocr.Word]:
    return [
        ocr.Word("Start", 100, 200, 60, 20, 95.0),
        ocr.Word("Cancel", 300, 400, 80, 24, 90.0),
    ]


def _one_word(_host: str, _port: int, _password: str | None, _min_confidence: float) -> list[ocr.Word]:
    return [ocr.Word("Start", 0, 0, 10, 10, 95.0)]


def _tesseract_absent() -> bool:
    return False


@pytest.mark.os_agnostic
def test_type_without_port_is_usage_error(managed_traceback_state: None) -> None:
    """A VNC command without --port is a usage error with a nonzero exit."""
    assert cli_mod.main(["type", "hello"], services_factory=build_production) != 0


@pytest.mark.os_agnostic
def test_unknown_subcommand_is_rejected(managed_traceback_state: None) -> None:
    """A subcommand the CLI does not define is a usage error."""
    assert cli_mod.main(["--port", "5901", "detect-layout"], services_factory=build_production) != 0


@pytest.mark.os_agnostic
def test_type_sends_text(monkeypatch: pytest.MonkeyPatch, managed_traceback_state: None) -> None:
    """type sends literal text and never touches tesseract."""
    typed: list[str] = []

    class _TypingClient(_FakeClient):
        def type_text(self, text: str) -> None:
            typed.append(text)

        def press(self, name: str) -> None:
            return None

    monkeypatch.setattr(vnc_cmd, "RfbClient", _TypingClient)
    assert cli_mod.main(["--port", "5901", "type", "a:|"], services_factory=build_production) == 0
    assert cli_mod.main(["--port", "5901", "type", "chkdsk c: /f", "--enter"], services_factory=build_production) == 0
    assert typed == ["a:|", "chkdsk c: /f"]


@pytest.mark.os_agnostic
def test_screenshot_prints_resolution_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    managed_traceback_state: None,
    tmp_path: object,
) -> None:
    """screenshot prints a parseable ``resolution: WxH`` line on stdout."""
    monkeypatch.setattr(vnc_cmd, "RfbClient", _FakeClient)
    out_file = str(tmp_path / "shot.png")  # type: ignore[operator]
    rc = cli_mod.main(["--port", "5901", "screenshot", out_file], services_factory=build_production)
    assert rc == 0
    assert "resolution: 1024x768" in capsys.readouterr().out


@pytest.mark.os_agnostic
def test_click_text_clicks_match_center(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    managed_traceback_state: None,
) -> None:
    """click-text finds the matching word and clicks its box center."""
    monkeypatch.setattr(vnc_cmd, "RfbClient", _FakeClient)
    monkeypatch.setattr(vnc_cmd, "_ocr_words", _two_words)
    _FakeClient.last_click = None

    rc = cli_mod.main(["--port", "5901", "click-text", "cancel"], services_factory=build_production)
    assert rc == 0
    assert _FakeClient.last_click == (340, 412)
    assert 'clicked "Cancel" at (340,412)' in capsys.readouterr().out


@pytest.mark.os_agnostic
def test_click_text_no_match_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    managed_traceback_state: None,
) -> None:
    """click-text exits nonzero when nothing matches."""
    monkeypatch.setattr(vnc_cmd, "RfbClient", _FakeClient)
    monkeypatch.setattr(vnc_cmd, "_ocr_words", _one_word)
    assert cli_mod.main(["--port", "5901", "click-text", "missing"], services_factory=build_production) != 0


@pytest.mark.os_agnostic
def test_ocr_missing_tesseract_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    managed_traceback_state: None,
) -> None:
    """ocr errors with a clear "tesseract is required" message when it is absent."""
    monkeypatch.setattr(vnc_cmd, "RfbClient", _FakeClient)
    monkeypatch.setattr(ocr, "tesseract_available", _tesseract_absent)
    rc = cli_mod.main(["--port", "5901", "ocr"], services_factory=build_production)
    assert rc != 0
    assert "tesseract is required" in capsys.readouterr().err


@pytest.mark.os_agnostic
def test_key_presses_named_key(monkeypatch: pytest.MonkeyPatch, managed_traceback_state: None) -> None:
    """key presses the named key on the guest."""
    pressed: list[str] = []

    class _PressClient(_FakeClient):
        def press(self, name: str) -> None:
            pressed.append(name)

    monkeypatch.setattr(vnc_cmd, "RfbClient", _PressClient)
    assert cli_mod.main(["--port", "5901", "key", "enter"], services_factory=build_production) == 0
    assert pressed == ["enter"]


@pytest.mark.os_agnostic
def test_click_clicks_pixel(monkeypatch: pytest.MonkeyPatch, managed_traceback_state: None) -> None:
    """click sends a left-button click at the given pixel."""
    monkeypatch.setattr(vnc_cmd, "RfbClient", _FakeClient)
    _FakeClient.last_click = None
    assert cli_mod.main(["--port", "5901", "click", "640", "480"], services_factory=build_production) == 0
    assert _FakeClient.last_click == (640, 480)


@pytest.mark.os_agnostic
def test_ocr_lists_words(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    managed_traceback_state: None,
) -> None:
    """ocr prints one parseable line per recognized word."""
    monkeypatch.setattr(vnc_cmd, "RfbClient", _FakeClient)
    monkeypatch.setattr(vnc_cmd, "_ocr_words", _two_words)
    rc = cli_mod.main(["--port", "5901", "ocr"], services_factory=build_production)
    assert rc == 0
    out = capsys.readouterr().out
    assert "130 210 60x20 conf=95 Start" in out
    assert "340 412 80x24 conf=90 Cancel" in out


@pytest.mark.os_agnostic
def test_parse_xy_accepts_pair_and_rejects_malformed() -> None:
    """The --mark callback parses X,Y and rejects bad input."""
    import rich_click as click

    assert vnc_cmd._parse_xy(None, None, None) is None  # type: ignore[arg-type]
    assert vnc_cmd._parse_xy(None, None, "12,34") == (12, 34)  # type: ignore[arg-type]
    with pytest.raises(click.BadParameter):
        vnc_cmd._parse_xy(None, None, "12")  # type: ignore[arg-type]


_TSV_SAMPLE = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    "5\t1\t1\t1\t1\t1\t100\t200\t60\t20\t95\tStart\n"
    "5\t1\t1\t1\t1\t2\t300\t400\t80\t24\t90\tCancel\n"
)


def _tesseract_present() -> bool:
    return True


def _fake_tsv(_png_path: str) -> str | None:
    return _TSV_SAMPLE


@pytest.mark.os_agnostic
def test_ocr_words_screenshots_then_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    """_ocr_words captures via the client, runs tesseract, and returns parsed words."""
    monkeypatch.setattr(vnc_cmd, "RfbClient", _FakeClient)
    monkeypatch.setattr(ocr, "tesseract_available", _tesseract_present)
    monkeypatch.setattr(ocr, "run_tesseract_tsv", _fake_tsv)
    words = vnc_cmd._ocr_words("127.0.0.1", 5901, None, ocr.DEFAULT_MIN_CONFIDENCE)  # type: ignore[reportPrivateUsage]
    assert [w.text for w in words] == ["Start", "Cancel"]
