# Module Reference: File Index and CLI

## Status

Current.

## Layout

The package follows clean architecture (enforced by import-linter): composition
imports adapters imports application imports domain, and domain is pure. The VNC
logic is the project's own domain and adapters; the config, logging, and email
subsystems are inherited from the bitranox CLI-application template.

## VNC source modules

- `domain/keymap.py` - named-key table and `char_keysym` (a character's keysym is
  its code point; the server owns the layout).
- `adapters/rfb.py` - `RfbClient`: RFB 003.008 handshake (None and VNC-password
  security), raw framebuffer capture, `screenshot` (PNG via Pillow), `click`,
  literal-keysym `type`/`press`, and the crosshair/grid overlays (PIL ImageDraw).
- `adapters/ocr.py` - tesseract TSV parsing into `Word` objects with click
  centers, plus matching helpers.
- `adapters/cli/commands/vnc.py` - the six VNC subcommands, wired into the root
  group in `adapters/cli/root.py`.

## Package and CLI plumbing

- `__init__.py` - public API (RfbClient, OCR helpers, keymap, metadata).
- `__init__conf__.py` - static package metadata constants and `print_info()`.
- `__main__.py` / `entry.py` - `python -m` shim and console-script entry, both
  wiring production services into `adapters/cli/main.py`.
- `adapters/cli/{main,root,context,exit_codes,typed_click,constants}.py` -
  rich-click CLI bootstrap, root group and global options, typed `CLIContext`,
  POSIX `ExitCode` enum, and the typed-decorator facade. `lib_cli_exit_tools`
  maps exceptions to exit codes.

## Inherited subsystems

`adapters/config`, `adapters/logging`, `adapters/email`, `adapters/memory`,
`application/ports.py`, and `composition/` provide layered configuration
(lib_layered_config), structured logging (lib_log_rich), and email (btx_lib_mail),
with their CLI commands (`info`, `config`, `config-deploy`,
`config-generate-examples`, `logdemo`, `send-email`, `send-notification`). See
`CONFIG.md` for configuration details. These are kept for house consistency and
are not used by VNC control itself.

## Tests

- `tests/test_keymap.py` - `char_keysym` and the named-key table.
- `tests/test_rfb.py` - the key-event wire sequence, the handshake (None and VNC
  auth), raw framebuffer decode, and PNG output, against a scripted socket.
- `tests/test_drawing.py` - crosshair and grid drawing on a PIL image.
- `tests/test_ocr.py` - TSV parsing, word centers, filtering, and match selection.
- `tests/test_cli_vnc.py` - the VNC subcommand wiring (client and OCR mocked).
- The remaining `tests/test_*.py` cover the inherited config/logging/email/CLI-core
  subsystems and package metadata.

## Dependencies

Runtime: rich-click, lib_cli_exit_tools, lib_log_rich, lib_layered_config,
btx_lib_mail, pydantic, orjson, pillow, cryptography. The OCR subcommands (`ocr`,
`click-text`) also shell out to the external `tesseract` binary, a required system
dependency, and error with a clear message when it is missing.

## CLI

Command: `vnc-remote-control`

Global options:

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--host HOST` | RFB server host (default: 127.0.0.1) |
| `--port PORT` | RFB server TCP port (required by the VNC subcommands) |
| `--password PASS` | VNC password (prefer the `VNC_REMOTE_CONTROL_PASSWORD` env var) |
| `--traceback / --no-traceback` | Show a full traceback on unexpected errors |
| `--profile NAME` | Load configuration from a named profile |
| `--set SECTION.KEY=VALUE` | Override a configuration setting (repeatable) |
| `--env-file PATH` | Explicit `.env` file path |
| `-h, --help` | Show help and exit |

VNC subcommands:

| Subcommand | Description |
|------------|-------------|
| `type TEXT [--enter]` | Type a string into the guest (literal keysyms) |
| `key NAME` | Press a single named key (enter, tab, esc, arrows, function keys) |
| `click X Y` | Left-click at a pixel position |
| `screenshot OUTFILE [--mark X,Y] [--grid N]` | Save the native-resolution framebuffer to a PNG; prints `resolution: WxH` |
| `ocr [--grep PATTERN] [--min-confidence N]` | List on-screen words with their click centers and confidence |
| `click-text PATTERN [--min-confidence N]` | Click the first on-screen word matching a pattern |

## Keyboard model

`type` sends literal keysyms (each character's keysym is its code point). A
layout-aware RFB server (openvmm is the example, via `--vnc-keyboard-layout`; on
Proxmox the ovm shim sets it from the VM `keyboard:` key) maps each keysym to the
guest's configured keyboard layout, so the client does no layout compensation and
the caller never needs to know the guest layout.

## Coordinate model

RFB PointerEvent coordinates are absolute framebuffer pixels, identical to the
pixels in a native-resolution screenshot. A coordinate read off such a screenshot
is the exact click coordinate. The tool never scales the framebuffer, and
`screenshot --mark X,Y` draws a crosshair so a caller can confirm a coordinate
before clicking it.
