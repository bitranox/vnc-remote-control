"""RFB key-event wire tests for the literal-keysym type path.

These exercise the byte sequence ``type_text`` emits, with a mock socket and no
live server. KeyEvent format is ``>BBHI`` = (msg_type=4, down_flag, pad=0, keysym).
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers import Cipher, modes

from vnc_remote_control.adapters.rfb import RfbClient, RfbError
from vnc_remote_control.domain import keymap

#: RFB security type byte for VNC password authentication.
_VNC_AUTH = 2

#: PNG file signature (the 8 magic bytes every PNG starts with).
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class _RecordingSocket:
    """Capture every ``sendall`` payload for later decoding."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)


def _key_events(sent: list[bytes]) -> list[tuple[int, int]]:
    """Decode captured payloads into (down_flag, keysym) KeyEvent tuples."""
    events: list[tuple[int, int]] = []
    for payload in sent:
        msg_type, down, _pad, keysym = struct.unpack(">BBHI", payload)
        assert msg_type == 4
        events.append((down, keysym))
    return events


def _no_sleep(_seconds: float) -> None:
    """Typed stand-in for time.sleep so the wire tests run instantly."""
    return None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> RfbClient:
    """An RfbClient wired to a recording socket, with sleeps disabled."""
    monkeypatch.setattr("vnc_remote_control.adapters.rfb.time.sleep", _no_sleep)
    c = RfbClient("127.0.0.1", 5901)
    c._sock = _RecordingSocket()  # type: ignore[assignment]
    return c


def _sent(client: RfbClient) -> list[bytes]:
    """Return the payloads captured by the recording socket."""
    sock = client._sock  # type: ignore[reportPrivateUsage]
    assert isinstance(sock, _RecordingSocket)
    return sock.sent


@pytest.mark.os_agnostic
def test_type_emits_literal_keysym_per_char(client: RfbClient) -> None:
    """Typing 'a:|' emits a plain down/up tap per char, no AltGr or Shift."""
    client.type_text("a:|")
    events = _key_events(_sent(client))
    assert events == [
        (1, ord("a")),
        (0, ord("a")),
        (1, ord(":")),
        (0, ord(":")),
        (1, ord("|")),
        (0, ord("|")),
    ]


@pytest.mark.os_agnostic
def test_type_has_no_modifier_wrapping(client: RfbClient) -> None:
    """No AltGr/Shift keysyms are sent around symbol characters."""
    client.type_text("@{[]}\\~|")
    events = _key_events(_sent(client))
    expected: list[tuple[int, int]] = []
    for ch in "@{[]}\\~|":
        expected.append((1, ord(ch)))
        expected.append((0, ord(ch)))
    assert events == expected


@pytest.mark.os_agnostic
def test_type_newline_emits_return(client: RfbClient) -> None:
    """A newline is sent as a Return tap, not a literal '\\n' keysym."""
    client.type_text("a\nb")
    events = _key_events(_sent(client))
    assert events == [
        (1, ord("a")),
        (0, ord("a")),
        (1, keymap.RETURN),
        (0, keymap.RETURN),
        (1, ord("b")),
        (0, ord("b")),
    ]


@pytest.mark.os_agnostic
def test_type_returns_none(client: RfbClient) -> None:
    """type_text returns nothing; every character is typed."""
    assert client.type_text("@|") is None


# -- handshake / framebuffer wire tests -------------------------------------


class _ScriptedSocket:
    """A socket double that replays canned server bytes and records sends.

    ``recv`` hands back the next slice of a preloaded byte script, so the same
    object can drive the full RFB handshake and a FramebufferUpdate without a
    live server.
    """

    def __init__(self, script: bytes) -> None:
        self._script = script
        self._pos = 0
        self.sent: list[bytes] = []

    def recv(self, n: int) -> bytes:
        chunk = self._script[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def close(self) -> None:
        return None


def _pixel_format() -> bytes:
    """A 32bpp little-endian true-colour pixel format (R<<16 | G<<8 | B)."""
    return (
        struct.pack(">BBBB", 32, 24, 0, 1)  # bpp, depth, big_endian=0, truecolour=1
        + struct.pack(">HHH", 255, 255, 255)  # max r, g, b
        + struct.pack(">BBB", 16, 8, 0)  # shift r, g, b
        + b"\x00\x00\x00"  # padding
    )


def _handshake(width: int, height: int, *, sec_types: bytes = b"\x01", sec_result: int = 0) -> bytes:
    """Build the server side of an RFB 003.008 None-security handshake."""
    return (
        b"RFB 003.008\n"  # 12-byte server protocol version
        + bytes([len(sec_types)])
        + sec_types
        + struct.pack(">I", sec_result)
        + struct.pack(">HH", width, height)
        + _pixel_format()
        + struct.pack(">I", 4)
        + b"vnc!"  # server name
    )


def _framebuffer(pixels: list[tuple[int, int, int]], rw: int, rh: int) -> bytes:
    """Build one raw-encoded FramebufferUpdate covering a single rectangle."""
    body = struct.pack(">BB", 0, 0)  # message-type 0, padding
    body += struct.pack(">H", 1)  # one rectangle
    body += struct.pack(">HHHH", 0, 0, rw, rh)  # x, y, w, h
    body += struct.pack(">i", 0)  # raw encoding
    for r, g, b in pixels:
        body += struct.pack("<I", (r << 16) | (g << 8) | b)
    return body


def _connected(
    monkeypatch: pytest.MonkeyPatch, script: bytes, *, password: str | None = None
) -> tuple[RfbClient, _ScriptedSocket]:
    """Return a client whose connect() consumed ``script`` from a scripted socket."""
    sock = _ScriptedSocket(script)

    def fake_create_connection(_address: tuple[str, int], timeout: float = 0.0) -> _ScriptedSocket:
        return sock

    monkeypatch.setattr("vnc_remote_control.adapters.rfb.socket.create_connection", fake_create_connection)
    client = RfbClient("127.0.0.1", 5901, password=password)
    client.connect()
    return client, sock


def _vnc_auth_handshake(width: int, height: int, challenge: bytes, *, sec_result: int = 0) -> bytes:
    """Build a server handshake that offers (only) VNC password authentication."""
    return (
        b"RFB 003.008\n"  # 12-byte server protocol version
        + bytes([1])
        + bytes([_VNC_AUTH])  # one security type: VNC auth
        + challenge  # 16-byte DES challenge
        + struct.pack(">I", sec_result)  # security result, after the client responds
        + struct.pack(">HH", width, height)
        + _pixel_format()
        + struct.pack(">I", 4)
        + b"vnc!"
    )


def _expected_vnc_response(password: str, challenge: bytes) -> bytes:
    """Independently compute the VNC-DES response (string-based bit reversal)."""
    raw = password.encode("latin-1")[:8].ljust(8, b"\x00")
    key = bytes(int(f"{byte:08b}"[::-1], 2) for byte in raw)
    encryptor = Cipher(TripleDES(key * 3), modes.ECB()).encryptor()  # noqa: S305
    return encryptor.update(challenge) + encryptor.finalize()


@pytest.mark.os_agnostic
def test_connect_vnc_auth_sends_correct_des_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """With a password, connect() selects VNC auth and sends the DES response."""
    password = "secret12"
    challenge = bytes(range(16))
    client, sock = _connected(monkeypatch, _vnc_auth_handshake(1024, 768, challenge), password=password)

    assert (client.width, client.height) == (1024, 768)
    assert bytes([_VNC_AUTH]) in sock.sent
    assert _expected_vnc_response(password, challenge) in sock.sent


@pytest.mark.os_agnostic
def test_connect_vnc_auth_required_without_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """A server offering only VNC auth, with no password supplied, errors clearly."""
    challenge = bytes(16)
    with pytest.raises(RfbError, match="requires a VNC password"):
        _connected(monkeypatch, _vnc_auth_handshake(800, 600, challenge))


@pytest.mark.os_agnostic
def test_connect_vnc_auth_wrong_password_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-zero security result after VNC auth reports an authentication failure."""
    challenge = bytes(16)
    with pytest.raises(RfbError, match="authentication failed"):
        _connected(monkeypatch, _vnc_auth_handshake(800, 600, challenge, sec_result=1), password="wrong")


@pytest.mark.os_agnostic
def test_connect_uses_none_when_password_set_but_only_none_offered(monkeypatch: pytest.MonkeyPatch) -> None:
    """A supplied password is ignored when the server only offers None security."""
    client, sock = _connected(monkeypatch, _handshake(640, 480), password="unused")
    assert (client.width, client.height) == (640, 480)
    assert bytes([1]) in sock.sent  # selected None, not VNC auth


@pytest.mark.os_agnostic
def test_connect_parses_geometry_and_selects_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """connect() reads width/height and selects the None security type."""
    client, sock = _connected(monkeypatch, _handshake(1024, 768))
    assert (client.width, client.height) == (1024, 768)
    # The client sent the protocol version, the None selection, and ClientInit.
    assert b"RFB 003.008\n" in sock.sent
    assert b"\x01" in sock.sent


@pytest.mark.os_agnostic
def test_connect_rejects_unsupported_security_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """A server offering only an unsupported security type fails the handshake."""
    with pytest.raises(RfbError, match="no supported security type"):
        _connected(monkeypatch, _handshake(800, 600, sec_types=b"\x13"))


@pytest.mark.os_agnostic
def test_connect_rejects_failed_security_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-zero security result aborts the handshake."""
    with pytest.raises(RfbError, match="security handshake failed"):
        _connected(monkeypatch, _handshake(800, 600, sec_result=1))


@pytest.mark.os_agnostic
def test_capture_decodes_raw_rectangle_to_rgb(monkeypatch: pytest.MonkeyPatch) -> None:
    """capture() decodes a raw 2x2 rectangle into the exact RGB buffer."""
    pixels = [(10, 20, 30), (40, 50, 60), (70, 80, 90), (100, 110, 120)]
    script = _handshake(2, 2) + _framebuffer(pixels, 2, 2)
    client, _sock = _connected(monkeypatch, script)

    img = client.capture()

    assert bytes(img) == bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])


@pytest.mark.os_agnostic
def test_capture_rejects_non_raw_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rectangle with a non-raw encoding is rejected."""
    update = struct.pack(">BB", 0, 0) + struct.pack(">H", 1)
    update += struct.pack(">HHHH", 0, 0, 1, 1) + struct.pack(">i", 7)  # encoding 7 = Tight
    client, _sock = _connected(monkeypatch, _handshake(1, 1) + update)
    with pytest.raises(RfbError, match="non-raw encoding"):
        client.capture()


@pytest.mark.os_agnostic
def test_screenshot_writes_a_valid_png(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """screenshot() writes a PNG with the right magic bytes and IHDR geometry."""
    pixels = [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)]
    script = _handshake(2, 2) + _framebuffer(pixels, 2, 2)
    client, _sock = _connected(monkeypatch, script)

    out = tmp_path / "shot.png"
    width, height = client.screenshot(str(out))

    assert (width, height) == (2, 2)
    png = out.read_bytes()
    assert png.startswith(_PNG_MAGIC)
    # IHDR width/height live right after the 8-byte magic + 4-byte length + "IHDR".
    assert struct.unpack(">II", png[16:24]) == (2, 2)
