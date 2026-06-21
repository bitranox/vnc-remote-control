# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.


## [0.1.0] 2026-06-22

### Added
- Initial release. A VNC/RFB remote-control CLI with the subcommands `type`,
  `key`, `click`, `screenshot`, `ocr`, and `click-text`, built on the bitranox
  CLI-application skeleton (clean architecture, rich-click, `lib_cli_exit_tools`).
- Literal-keysym typing: `type` sends each character's keysym (its code point),
  the way a standard VNC client does. The guest keyboard layout is a server-side
  setting (a layout-aware server such as openvmm maps the keysyms), so the client
  does no layout compensation.
- Coordinate model with no scaling: screenshot pixels equal click coordinates,
  with `--mark X,Y` and `--grid N` overlays to confirm a coordinate.
- OCR-based commands (`ocr`, `click-text`) that report and click on-screen text.
- Authentication: None and VNC-password (DES challenge) security types. Pass a
  password with `--password` or the `VNC_REMOTE_CONTROL_PASSWORD` environment
  variable.
- Screenshots are written as PNG with Pillow.

### Requirements
- Runtime dependencies: rich-click, lib_cli_exit_tools, lib_log_rich,
  lib_layered_config, btx_lib_mail, pydantic, orjson, pillow, cryptography.
- tesseract is a required system dependency for the OCR commands `ocr` and
  `click-text`. Install `tesseract-ocr` (Debian/Ubuntu), `tesseract` (macOS via
  brew, Windows via choco). `type`, `key`, `click`, and `screenshot` do not need
  it.
