"""RFB (VNC) client over the wire, pure standard library.

``RfbClient`` connects to an RFB server, performs the RFB 003.008 handshake with
the None security type, and exposes the four operations this tool needs:

  * ``screenshot`` writes the current framebuffer to a PNG file.
  * ``click`` sends a left-button press and release at a pixel position.
  * ``tap`` sends a key press and release for one keysym.
  * ``type_text`` types a string by sending one literal keysym per character.
    The server owns the layout: a layout-aware server (such as openvmm) maps each
    keysym to the guest's configured keyboard layout, so this client does no
    translation.
  * ``press`` sends a single named key (enter, tab, esc, and so on).

The framebuffer is requested with raw encoding only and decoded here; the decoded
RGB buffer is written to disk as a PNG with Pillow.
"""

from __future__ import annotations

import socket
import struct
import time

from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from PIL import Image, ImageDraw

from ..domain import keymap
from ..domain.timing import RfbTimings

#: RFB security type for no authentication.
_SECURITY_NONE = 1
#: RFB security type for VNC password authentication (DES challenge-response).
_VNC_AUTH = 2
#: Mask for one byte, used when reversing the bit order of a DES key byte.
_BYTE_BITS = 8


def _reverse_bits(byte: int) -> int:
    """Reverse the bit order of a single byte (the VNC DES key quirk).

    >>> _reverse_bits(0b00000001)
    128
    >>> _reverse_bits(0b10110000)
    13
    """
    result = 0
    for i in range(_BYTE_BITS):
        result |= ((byte >> i) & 1) << (_BYTE_BITS - 1 - i)
    return result


class RfbError(Exception):
    """Raised when the RFB handshake or protocol exchange fails."""


class RfbClient:
    """A minimal RFB client speaking RFB 003.008.

    Supports the None and VNC-password (DES challenge) security types. Pass a
    ``password`` to authenticate against a server that requires VNC auth; without
    one, only servers offering None security are accepted.

    Use as a context manager so the socket is always closed::

        with RfbClient("127.0.0.1", 5901) as client:
            client.type_text("hello")
    """

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 15.0,
        password: str | None = None,
        timings: RfbTimings | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.password = password
        self._timings = timings or RfbTimings()
        self._sock: socket.socket | None = None
        self.width = 0
        self.height = 0
        self._pixel_format: bytes = b""

    # -- connection / handshake ----------------------------------------------
    def __enter__(self) -> RfbClient:
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def connect(self) -> None:
        """Open the socket and run the RFB 003.008 handshake (None or VNC auth)."""
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock = sock
        self._read(12)  # server protocol version
        sock.sendall(b"RFB 003.008\n")
        n_types = self._read(1)[0]
        if n_types == 0:
            # A zero type count means the server refused; a reason string follows.
            reason_len = struct.unpack(">I", self._read(4))[0]
            reason = self._read(reason_len).decode("latin-1", "replace")
            raise RfbError(f"server refused the connection: {reason}")
        self._authenticate(self._read(n_types))
        sock.sendall(b"\x01")  # ClientInit, shared
        self.width, self.height = struct.unpack(">HH", self._read(4))
        self._pixel_format = self._read(16)
        name_len = struct.unpack(">I", self._read(4))[0]
        self._read(name_len)  # server name, ignored

    def _authenticate(self, types: bytes) -> None:
        """Select a security type, run its exchange, and check the result."""
        sock = self._conn()
        if self.password is not None and _VNC_AUTH in types:
            sock.sendall(bytes([_VNC_AUTH]))
            sock.sendall(self._vnc_des_response(self._read(16)))
        elif _SECURITY_NONE in types:
            sock.sendall(bytes([_SECURITY_NONE]))
        elif _VNC_AUTH in types:
            raise RfbError("server requires a VNC password; pass one with --password")
        else:
            raise RfbError(f"server offers no supported security type; got {list(types)}")
        if struct.unpack(">I", self._read(4))[0] != 0:
            if self.password is not None:
                raise RfbError("VNC authentication failed (wrong password?)")
            raise RfbError("RFB security handshake failed")

    def _vnc_des_response(self, challenge: bytes) -> bytes:
        """Encrypt the 16-byte challenge with the VNC-DES of the password.

        VNC keys DES with the first 8 password bytes (zero-padded), but with the
        bit order of each key byte reversed. The 16-byte challenge is two ECB
        blocks.
        """
        raw = (self.password or "").encode("latin-1")[:8].ljust(8, b"\x00")
        key = bytes(_reverse_bits(b) for b in raw)
        # DES-ECB is mandated by the RFB VNC-auth spec, not a choice; every VNC
        # server expects exactly this challenge-response, so it cannot be AES.
        # VNC uses single DES; 3DES with K1=K2=K3 (key repeated to 24 bytes) is
        # identical to it and avoids the deprecated 8-byte single-key form.
        encryptor = Cipher(TripleDES(key * 3), modes.ECB()).encryptor()  # noqa: S305 # nosec B305
        return encryptor.update(challenge) + encryptor.finalize()

    def close(self) -> None:
        """Close the socket if open."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    # -- low-level I/O -------------------------------------------------------
    def _conn(self) -> socket.socket:
        if self._sock is None:
            raise RfbError("not connected; call connect() first")
        return self._sock

    def _read(self, n: int) -> bytes:
        sock = self._conn()
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise RfbError(f"connection closed: wanted {n} bytes, got {len(buf)}")
            buf += chunk
        return buf

    # -- pointer / keyboard --------------------------------------------------
    def _pointer(self, mask: int, x: int, y: int) -> None:
        self._conn().sendall(struct.pack(">BBHH", 5, mask, x, y))

    def click(self, x: int, y: int) -> None:
        """Send a left-button click at pixel position ``(x, y)``."""
        self._pointer(0, x, y)
        time.sleep(self._timings.click_move_gap)
        self._pointer(1, x, y)
        time.sleep(self._timings.click_hold)
        self._pointer(0, x, y)
        time.sleep(self._timings.click_release_gap)

    def _key(self, keysym: int, *, down: bool) -> None:
        """Send a single KeyEvent (down or up) for ``keysym``."""
        self._conn().sendall(struct.pack(">BBHI", 4, 1 if down else 0, 0, keysym))

    def tap(self, keysym: int) -> None:
        """Send a key down then key up for ``keysym``."""
        self._key(keysym, down=True)
        time.sleep(self._timings.key_down_hold)
        self._key(keysym, down=False)
        time.sleep(self._timings.key_up_gap)

    def press(self, name: str) -> None:
        """Send a single named key such as "enter", "tab", or "esc"."""
        key = name.lower()
        if key not in keymap.NAMED_KEYS:
            known = ", ".join(sorted(keymap.NAMED_KEYS))
            raise ValueError(f"unknown key name {name!r}; known: {known}")
        self.tap(keymap.NAMED_KEYS[key])

    def type_text(self, text: str) -> None:
        """Type ``text`` by sending one literal keysym per character.

        Each character's keysym is its code point; the layout-aware server maps
        it to the guest's keyboard layout. A newline is sent as Return.
        """
        for ch in text:
            if ch == "\n":
                self.tap(keymap.RETURN)
                continue
            self.tap(keymap.char_keysym(ch))

    # -- framebuffer ---------------------------------------------------------
    def capture(self) -> bytearray:
        """Request the full framebuffer and return it as a 24-bit RGB buffer.

        The buffer is ``width * height * 3`` bytes at the native resolution. No
        scaling is applied, so the pixel coordinates in this buffer are the same
        absolute framebuffer coordinates a PointerEvent uses.
        """
        sock = self._conn()
        pf = self._pixel_format
        bpp, _depth, big_endian = pf[0], pf[1], pf[2]
        max_r, max_g, max_b = struct.unpack(">HHH", pf[4:10])
        shift_r, shift_g, shift_b = pf[10], pf[11], pf[12]

        # SetEncodings: raw only.
        sock.sendall(struct.pack(">BBH", 2, 0, 1) + struct.pack(">i", 0))
        # FramebufferUpdateRequest, full and non-incremental.
        sock.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, self.width, self.height))

        msg_type = self._read(1)[0]
        if msg_type != 0:
            raise RfbError(f"unexpected server message {msg_type}")
        self._read(1)  # padding
        n_rects = struct.unpack(">H", self._read(2))[0]

        width, height = self.width, self.height
        img = bytearray(width * height * 3)
        bytes_per_pixel = bpp // 8
        for _ in range(n_rects):
            rx, ry, rw, rh = struct.unpack(">HHHH", self._read(8))
            enc = struct.unpack(">i", self._read(4))[0]
            if enc != 0:
                raise RfbError(f"non-raw encoding {enc} not supported")
            data = self._read(rw * rh * bytes_per_pixel)
            order = "big" if big_endian else "little"
            for j in range(rh):
                for i in range(rw):
                    offset = (j * rw + i) * bytes_per_pixel
                    px = int.from_bytes(data[offset : offset + bytes_per_pixel], order)
                    r = ((px >> shift_r) & max_r) * 255 // max_r
                    g = ((px >> shift_g) & max_g) * 255 // max_g
                    b = ((px >> shift_b) & max_b) * 255 // max_b
                    pos = (((ry + j) * width) + (rx + i)) * 3
                    img[pos] = r
                    img[pos + 1] = g
                    img[pos + 2] = b
        return img

    def screenshot(
        self,
        out_path: str,
        mark: tuple[int, int] | None = None,
        grid: int | None = None,
    ) -> tuple[int, int]:
        """Capture the framebuffer and write it to ``out_path`` as a native-res PNG.

        With ``grid`` set, faint gridlines are drawn every ``grid`` pixels. With
        ``mark`` set, a high-contrast crosshair is drawn through that point. Both
        draw on the captured image before it is saved, so the PNG stays at native
        resolution and the marked pixel is the exact click coordinate. Returns the
        ``(width, height)`` of the captured screen.
        """
        width, height = self.width, self.height
        image = Image.frombytes("RGB", (width, height), bytes(self.capture()))
        if grid is not None and grid > 0:
            draw_grid(image, grid)
        if mark is not None:
            draw_crosshair(image, mark[0], mark[1])
        image.save(out_path, format="PNG")
        return width, height


# -- overlay drawing on the captured image ------------------------------------
#: Crosshair and box color (magenta) chosen for contrast against typical UIs.
_MARK_RGB = (255, 0, 255)
#: Gridline color (medium gray), blended at half strength over the image.
_GRID_RGB = (128, 128, 128)
#: Half-size of the hollow box drawn around a marked point.
_BOX_HALF = 6
#: Alpha used to blend the faint gridlines (128/255, i.e. roughly half strength).
_GRID_ALPHA = 128


def draw_crosshair(image: Image.Image, x: int, y: int) -> None:
    """Draw a full-span crosshair through ``(x, y)`` plus a hollow box around it.

    The crosshair is two 1px magenta lines spanning the whole image, so it is easy
    to confirm the lines cross exactly on the intended target. Coordinates outside
    the image are clipped by the drawing layer.
    """
    width, height = image.size
    draw = ImageDraw.Draw(image)
    draw.line([(0, y), (width - 1, y)], fill=_MARK_RGB)
    draw.line([(x, 0), (x, height - 1)], fill=_MARK_RGB)
    draw.rectangle((x - _BOX_HALF, y - _BOX_HALF, x + _BOX_HALF, y + _BOX_HALF), outline=_MARK_RGB)


def draw_grid(image: Image.Image, step: int) -> None:
    """Blend faint gridlines every ``step`` pixels (vertical and horizontal).

    The lines are composited at half strength so they read as a coordinate ruler
    without hiding the content underneath.
    """
    if step <= 0:
        return
    width, height = image.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    line_rgba = (*_GRID_RGB, _GRID_ALPHA)
    for gx in range(step, width, step):
        draw.line([(gx, 0), (gx, height - 1)], fill=line_rgba)
    for gy in range(step, height, step):
        draw.line([(0, gy), (width - 1, gy)], fill=line_rgba)
    blended = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    image.paste(blended)
