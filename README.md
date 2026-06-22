# vnc-remote-control

<!-- Badges -->
[![CI](https://github.com/bitranox/vnc-remote-control/actions/workflows/default_cicd_public.yml/badge.svg)](https://github.com/bitranox/vnc-remote-control/actions/workflows/default_cicd_public.yml)
[![CodeQL](https://github.com/bitranox/vnc-remote-control/actions/workflows/codeql.yml/badge.svg)](https://github.com/bitranox/vnc-remote-control/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open in Codespaces](https://img.shields.io/badge/Codespaces-Open-blue?logo=github&logoColor=white&style=flat-square)](https://codespaces.new/bitranox/vnc-remote-control?quickstart=1)
[![PyPI](https://img.shields.io/pypi/v/vnc-remote-control.svg)](https://pypi.org/project/vnc-remote-control/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vnc-remote-control.svg)](https://pypi.org/project/vnc-remote-control/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-46A3FF?logo=ruff&labelColor=000)](https://docs.astral.sh/ruff/)
[![codecov](https://codecov.io/gh/bitranox/vnc-remote-control/graph/badge.svg)](https://codecov.io/gh/bitranox/vnc-remote-control)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)


A small command-line tool to drive a VNC/RFB server: type text, press named keys,
click, and grab a screenshot. It speaks plain RFB (None or VNC-password security,
raw encoding) and sends literal keysyms like a standard VNC client, so it works
with any VNC/RFB server; the guest keyboard layout is a server-side setting, not
something this client compensates for. A layout-aware server such as openvmm is
the ideal target (see the keyboard section), but it is not required.

The CLI is styled with [rich-click](https://github.com/ewels/rich-click); the RFB
protocol and pixel drawing are pure standard library, and screenshots are written
as PNG with [Pillow](https://python-pillow.org/). The tool also needs one external
program: tesseract, used for OCR. See the Install section.

## When this is useful

The connection is to a VNC/RFB server, so nothing runs on the target machine. That
makes the tool a good fit when:

- **A machine has no network of its own.** A VM that isn't on the network yet (or
  never will be) can still be driven through its hypervisor's VNC console, the same
  screen you'd click in the web UI. This is handy for the first-boot setup where you
  configure networking before the guest can reach anything.
- **You want Claude to operate a machine with no footprint on it.** Nothing is
  installed on the guest: no agent, no service, no open port on the target, nothing
  visible in its process list. The control happens entirely over the host's VNC.
- **A box is only reachable over VNC.** For remote administration where VNC is the
  one door you have, this drives it the same way a person at the console would.
- **Legacy desktop software has only a GUI.** Old line-of-business apps, dated
  installers, and vendor tools often have no API, CLI, or accessibility tree to
  automate against, only a window. Reading the screen with OCR and clicking by
  label drives them when nothing else can, and legacy UIs rarely change layout, so
  the coordinates stay stable.

## What it does

- `type` a string into the focused guest field (literal keysyms).
- `key` presses a single named key (enter, tab, esc, arrows, function keys).
- `click` sends a left-button click at a pixel position.
- `screenshot` writes the native-resolution framebuffer to a PNG file, with
  optional crosshair and grid overlays.
- `ocr` lists the words on screen with their click centers and confidence.
- `click-text` clicks the first on-screen word matching a pattern.

## Install

### Prerequisite: tesseract

tesseract is a required system dependency. OCR is core to the tool (it is how an
LLM finds what to click via `ocr` and `click-text`), so install it first:

```bash
# Debian/Ubuntu
sudo apt-get install tesseract-ocr
# macOS
brew install tesseract
# Windows
choco install tesseract
```

### The package

With pip:

```bash
pip install vnc-remote-control
```

With uv:

```bash
uv tool install vnc-remote-control
```

From a checkout:

```bash
pip install -e .
```

For alternative install paths (pip, pipx, uv, uvx, source builds), see
[INSTALL.md](INSTALL.md). Every supported method registers the
`vnc-remote-control` command on your PATH.

## Usage

The CLI uses [rich-click](https://github.com/ewels/rich-click), so help output and
validation errors render with Rich styling while keeping the familiar click
ergonomics. Every command needs `--port`. The host defaults to `127.0.0.1`.

```bash
# type a command and press Return
vnc-remote-control --port 5901 type "chkdsk c: /f" --enter

# type any characters; the server maps them to the guest layout
vnc-remote-control --port 5901 type "user@host"

# press a single key
vnc-remote-control --port 5901 key enter
vnc-remote-control --port 5901 key esc

# click at a pixel position
vnc-remote-control --port 5901 click 640 480

# screenshot to a PNG (prints "resolution: WxH" on stdout)
vnc-remote-control --port 5901 screenshot /tmp/guest.png

# screenshot with a crosshair through a candidate click point
vnc-remote-control --port 5901 screenshot /tmp/guest.png --mark 640,480

# screenshot with a 50px coordinate grid
vnc-remote-control --port 5901 screenshot /tmp/guest.png --grid 50

# list on-screen words with their click centers
vnc-remote-control --port 5901 ocr
vnc-remote-control --port 5901 ocr --grep "Sign in"

# click the first on-screen word matching a pattern
vnc-remote-control --port 5901 click-text "Next"

# against a remote host
vnc-remote-control --host 10.0.0.5 --port 5901 key f8
```

You can also run it as a module: `python -m vnc_remote_control --port 5901 key enter`.

## Authentication

Servers offering None security (an openvmm/hypervisor console on localhost is the
typical case) need nothing. For a server that requires a VNC password, pass one
with the global `--password` option; the client then does the standard VNC DES
challenge-response.

A password on the command line is visible in the process list, so prefer the
`VNC_REMOTE_CONTROL_PASSWORD` environment variable, which `--password` reads by
default:

```bash
# preferred: password via environment
VNC_REMOTE_CONTROL_PASSWORD=secret vnc-remote-control --port 5901 key enter

# or explicitly (visible in `ps`)
vnc-remote-control --port 5901 --password secret screenshot /tmp/guest.png
```

Apple Remote Desktop and TLS/VeNCrypt auth are not supported.

## Timing (sluggish guests)

Each key and click is sent as a down edge, a short delay, then an up edge. The
default delays are tuned so a normal guest registers every event, but a sluggish
guest (an old desktop, a loaded VM, legacy software that repaints slowly) can drop
events typed too fast. There are two ways to slow things down:

- **Quick knob:** the global `--delay-scale` option multiplies every delay. For a
  guest that misses keystrokes, try doubling them:

  ```bash
  vnc-remote-control --port 5901 --delay-scale 2 type "slow guest"
  ```

- **Per-delay config:** the `[vnc]` section sets the individual delays (seconds).
  Set them in a config file, via environment variables, or with `--set`:

  ```bash
  vnc-remote-control --port 5901 --set vnc.key_up_gap=0.2 type "hi"
  ```

  The keys are `key_down_hold`, `key_up_gap`, `click_move_gap`, `click_hold`, and
  `click_release_gap`; see `CONFIG.md` and the bundled defaults for the documented
  values. `--delay-scale` applies on top of whatever the config resolves to.

## Driving with an LLM (Claude)

The point of this tool is to let an LLM see the guest screen and click the right
place every time. The key fact: RFB pointer coordinates are absolute framebuffer
pixels, the same pixels in a native-resolution screenshot. So a coordinate read
off the screenshot is the exact coordinate to click. Past "wrong pixel" failures
came from reading coordinates off a scaled image; this tool never scales.

The loop:

1. Capture and look. Run `screenshot out.png`. The command prints
   `resolution: WxH` on stdout. View `out.png` at native size (do not let your
   viewer downscale it).
2. Read coordinates directly. Any (x, y) you read off `out.png` is the click
   coordinate. There is no scale factor to undo.
3. Verify a coordinate before committing. Run
   `screenshot out.png --mark X,Y` and check the crosshair crosses exactly on
   the target. `--grid 50` adds a coordinate grid if you want a ruler.
4. Click. Either click the verified pixel with `click X Y`, or, more reliably,
   click by label: run `ocr --grep "Sign in"` to get the word's center
   `<cx> <cy>` and `click <cx> <cy>`, or do it in one shot with
   `click-text "Sign in"`. Clicking by label avoids guessing pixels entirely.
5. Focus, then type. A window you just opened or launched (taskbar search, the
   Run box, a freshly launched app) often does NOT have keyboard focus yet.
   Click into the target text field first, then `type`. Skipping the click is
   the most common reason text appears to go nowhere: a freshly-opened editor
   showed nothing typed until it was clicked to focus. Then use `type` (with
   `--enter`) and `key`.

## Focus before typing

Typing goes to whatever has keyboard focus, which is not always the window you
just opened. After you open or launch anything (a search result, the Run box, an
application), click into the actual text field before you `type`. If text seems to
vanish, the field was not focused: screenshot, click the field, and type again.

## Keyboard layout (server-side)

The caller never needs to know the guest's keyboard layout. Neither does an LLM
driving this tool. You pass the text you want typed, and that is all the
knowledge required on this side.

Here is why. There is no local keyboard in the loop: the `type` argument is
already a string of Unicode characters, and the client puts each character's
code point straight on the wire as its keysym (to type `|` it sends `0x7C`, to
type `ä` it sends `0xE4`), exactly like a standard VNC client. Your own laptop's
layout is irrelevant; the same bytes go out whether you are on a US, German, or
Dvorak keyboard. The client does NOT reverse-map characters or juggle AltGr.

The layout lives in exactly one place: the server. A layout-aware RFB server maps
each keysym to the guest's configured layout. openvmm is the concrete example: its
`--vnc-keyboard-layout` flag (on Proxmox the ovm shim derives it from the VM's
`keyboard:` key) tells it the guest's layout, and it works backwards from the
character you asked for to the physical keypress that produces it on that layout.
So as long as the server's configured layout matches the guest's actual layout,
every character types correctly, and there is nothing to detect or compensate for
on this side.

It only goes wrong if the server is told the wrong layout (its setting does not
match the guest). The fix is never on the client: correct the server's layout to
match the guest. A driving LLM would *see* the wrong characters land in a
screenshot and can flag it, but it does not, and should not, try to compensate
per keystroke.

Plainer VNC servers that map keysyms assuming a fixed (often US) layout still work
for any text that layout can produce; a layout-aware server such as openvmm is
what makes arbitrary characters and non-US layouts type reliably.

## Further Documentation

- [Install Guide](INSTALL.md)
- [Development Handbook](DEVELOPMENT.md)
- [Contributor Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Module Reference](docs/systemdesign/module_reference.md)
- [License](LICENSE)

## AI transparency

This project was built with AI assistance. See [ai-disclosure.md](ai-disclosure.md)
for exactly how, and [ai-stance.md](ai-stance.md) for the reasoning behind it.

## License

MIT. See [LICENSE](LICENSE).
