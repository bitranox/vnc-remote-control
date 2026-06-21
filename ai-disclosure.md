# AI disclosure

An honest account of the role AI played in this repository. For the general
position behind it, see [ai-stance.md](ai-stance.md).

## Summary

The maintainer ([bitranox](https://github.com/bitranox)) designed, directed, and
verified this project. An AI coding assistant (Anthropic's Claude, via the Claude
Code CLI) was a tool used to speed up the routine work, always under the
maintainer's direction and review. Every decision, and the final result, are the
maintainer's. The work was done in 2026 and the history is in this repository's
git log.

## What the maintainer drove

- **Set the goal and the approach.** Build a remote-control client for a VNC/RFB
  server that an LLM can use to drive a guest: type, press keys, click, screenshot,
  and find what to click. Build it on the house CLI-application skeleton so it
  shares the project family's standard layout, exit handling, configuration, and
  logging, with the VNC logic carried as its own domain and commands.
- **Made the design decisions.** Two calls shape the whole tool. First, the
  keyboard model: the server owns the layout, so the client sends literal keysyms
  and never reverse-maps characters or juggles AltGr. A layout-aware server such as
  openvmm maps each keysym to the guest layout. Second, the coordinate model: never
  scale anything, so a pixel read off a native-resolution screenshot is the exact
  pixel to click. That second decision came directly out of real "wrong pixel"
  failures caused by reading coordinates off a downscaled image.
- **Decided what the tool should and shouldn't do.** Keep the RFB protocol in the
  standard library (sockets and struct), write screenshots as PNG with Pillow, and
  use OCR (`ocr`, `click-text`) so an LLM can click by label instead of guessing
  pixels. Support None and VNC-password security with raw encoding, so it works
  against any VNC/RFB server.
- **Verified it against a live server.** What counts as "correct" here is that a
  typed string lands in the right field and a click lands on the right pixel of a
  real guest. That was checked by running the tool against a live VNC/RFB server,
  not assumed from the code.
- **Reviewed every change**, and maintains and answers for the result.

## Where AI helped

Under that direction, the assistant did the legwork: drafting the RFB client
(`rfb.py`, including the handshake, the raw-encoding framebuffer decode, and the
hand-written PNG writer), the keysym map, the tesseract TSV parsing (`ocr.py`), and
the VNC command surface (`adapters/cli/commands/vnc.py`) that plugs into the house
CLI skeleton (clean architecture with domain, application, adapters, and
composition layers; rich-click; `lib_cli_exit_tools` for exit handling). It also
wrote the unit tests, doctests, and docs. The maintainer checked and accepted all
of it rather than taking it on trust.

## What this means for you

Judge it the way you'd judge any other code. The behavior is documented, the
parsing and drawing logic is unit-tested, the type surface is checked under pyright
strict, the layer boundaries are enforced by import-linter, and there is a
maintainer behind it. The OCR and RFB paths are best confirmed against your own
server. Issues and pull requests are welcome. `make test` runs the full suite
without a live guest.
