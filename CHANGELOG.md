# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.


## [Unreleased]

## [0.2.2] 2026-06-22

### Documentation
- Driving-with-an-LLM skill: documents authentication (VNC has no username, only a
  password, passed via `--password` or the `VNC_REMOTE_CONTROL_PASSWORD` environment
  variable) and adds connection (`--host`/`--port`) and `--delay-scale` examples.

## [0.2.1] 2026-06-22

### Changed
- Release/CI workflows synced from the `default_cicd_public` template: PyPI publish
  now uses hybrid auth (API token, or OIDC Trusted Publisher when no token secret is
  set), and CI adds an import-linter architecture gate.

### Documentation
- README: clarified that the tool is a pure client, installed only on the control or
  development box, with nothing on the targets.
- Driving-with-an-LLM skill: documents the `--password` and `--delay-scale` global
  options, adds a `click-text` fallback for low-contrast or placeholder text, and
  generalizes the server-side keyboard-layout wording (openvmm as an example, not a
  requirement).

## [0.2.0] 2026-06-22

### Added
- Tunable key/click timing for sluggish or legacy guests. A global `--delay-scale`
  option multiplies every event delay, and a `[vnc]` configuration section sets the
  individual delays (`key_down_hold`, `key_up_gap`, `click_move_gap`, `click_hold`,
  `click_release_gap`) via config files, environment variables, or `--set`.
- `RfbTimings` value object in the public API; `RfbClient` now accepts a `timings`
  parameter.
- README "When this is useful" documents driving legacy desktop software that has
  only a GUI (no API, CLI, or accessibility tree).

### Fixed
- Corrected stale template leftovers and non-ASCII characters in CONFIG.md.

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
