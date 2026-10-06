# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.


## [Unreleased]

### Changed
- **Requires lib_layered_config 7.0.1.** An unquoted `.env` value now converts like the
  environment layer, so `EMAIL__USE_STARTTLS=false` arrives as the boolean `false` rather than
  the string `"false"`.
- **Exit code change: an invalid `--profile` name exits 2.** A name such as `../x` given to the
  root's `--profile` or to `config --profile` escaped as a `ValueError` (exit 22, `info` and
  `hello` included), and given to `config-deploy --profile` failed as "Failed to deploy
  configuration" (exit 1). All three are now usage errors (exit 2). A profile FILE that does not
  load exits 78.
- **Exit code change: a configuration that does not load exits 78** for the commands that read it
  (see Fixed), where it used to exit 1 from every command.
- **`click` is a declared dependency.** The package imports it directly (`adapters/cli/main.py`,
  `commands/config.py`) but only had it through rich-click. A new test fails when a runtime
  import is missing from `[project].dependencies`.

### Fixed
- **`email.smtp_hosts` and `email.recipients` set to nothing mean not configured.** A bare YAML
  key or an environment `null` was refused as "Input should be a valid list" for both settings.
  Both now read `None` as an empty list.
- **`build_testing()` can run a command.** The in-memory logging initializer was a no-op while every
  command binds job context onto the lib_log_rich runtime, so any command under the testing
  composition raised `RuntimeError('lib_log_rich.init() must be called before using the logging
  API')`. It now starts a quiet runtime (no journald, event log, Graylog or queue; console at ERROR;
  no `.env` loading). Under `build_testing()` a command's `logger.error` line now reaches stderr
  ahead of its `Error:` line.
- **No more `SystemExit: N` on stderr.** The email and config commands and `click-text` (when no
  on-screen text matched) raised a bare `SystemExit`, which `main()`'s catch-all branch printed as
  `SystemExit: 78` (or `: 1`) after the real error message. They now exit through click's context
  (`ctx.exit`), and `main()` returns the exit code rich_click's `main()` hands back instead of
  discarding it. Exit codes are unchanged. `typed_click` gains a typed `get_current_context`
  wrapper for the helpers that have no `ctx` parameter.
- **A failed send is reported once.** click's `Exit` subclasses `RuntimeError`, so the send-result
  exit raised inside the delivery `try` was caught again by the `DeliveryError`/`RuntimeError`
  branch, adding "SMTP delivery failed" to the correct "sending failed". The send result is
  handled in the `try`'s `else`, and `config-deploy` re-raises an `Exit` before its catch-all.
- **A broken configuration file no longer disables every command.** The root group loaded the
  configuration before any subcommand option was parsed and let a load error escape, so a
  malformed `config.toml` made every command, `--help` and `config-deploy` (the command that
  replaces the file) exit 1 with empty stdout. The root now records the failure
  (`adapters/cli/config_load.py`); `config`, `send-email`, `send-notification` and the VNC
  commands that open a connection with the configured timings (`type`, `key`, `click`,
  `screenshot`, `click-text`) refuse with exit 78 and one line naming it, while `config-deploy`
  (with a warning), `config-generate-examples`, `ocr`, `info`, `hello` and help still run. An
  unreadable file takes the same path, and so does an `--env-file` that is not UTF-8 (the line
  names the file). `--traceback` prints the loader's chained traceback before the line. Any other
  exception from the loader is a bug and propagates as one.
- **Command-line mistakes are usage errors, checked before loading.** A malformed `--set` or an
  invalid `--profile` name is refused with exit 2 for every command, `info` and `hello` included,
  so a broken file cannot hide it. So are two `--set` values that give one key a value and put a
  key under it (`--set a.b=1 --set a.b.c=2`), which escaped as a `TypeError` (exit 22) in one order
  and silently dropped the earlier value in the other. `config --profile X` reloads with the
  root's `--env-file` instead of searching for another `.env`.

### Security
- **An attachment allow or block list in the wrong form is refused, not dropped.** The
  `[email.attachments]` lists `allowed_extensions`, `blocked_extensions`, `allowed_directories`
  and `blocked_directories` read any value that was not a list as "not configured", so a
  comma-separated environment value (`.pdf,.txt`, which arrives as one string; only a JSON array
  `[".pdf", ".txt"]` arrives as a list) silently replaced the configured list with btx_lib_mail's
  defaults: a configured whitelist was lifted, a configured blacklist replaced. Such a value, and
  a number, boolean or table, is now refused: `send-email` and `send-notification` exit 78 with
  `Error: Invalid configuration - ... attachment_<key>: expected a list ...`. An empty value
  (`[]`, an empty or whitespace-only string) still means "not configured". From Python, a tuple
  is read like a list and a set like a frozenset (an empty one still disables the list).
  `smtp_hosts` and `recipients` no longer empty a tuple or a non-list value: a tuple is read as a
  list, a number is refused.

## [1.0.4] 2026-07-30 18:36:36

### Changed

- **The shipped skill's plugin version now tracks the package version.** bmk 3.14.0 raises
  `.claude-plugin/plugin.json` to the package version on bump, push and release, and never lowers
  it. An install re-fetches a skill only when that version changes, so the two numbers drifting
  apart meant a skill edit could ship to nobody. No functional change.

## [1.0.3] - 2026-07-30

### Changed

- **Version line raised past the shipped skill's.** The Claude Code plugin in
  `.claude-plugin/plugin.json` was at 1.0.2 while the package was at 0.2.3, because the skill
  ships more often than the package it documents. bmk now slaves the plugin version to the
  package version, and that sync must never move an install backward, so the package version
  is raised past it once here. No functional change; the crossing of 1.0 is a consequence of
  that alignment, not a stability claim made on its own.

## [0.2.3] 2026-07-24 13:52:16

### Fixed
- Latest ruff now enforces `PLR0917` (too many positional arguments): CLI command
  callbacks and the internal `_execute_deploy` helper take their options
  keyword-only, matching how Click already invokes them.
- A doctest in `permissions.get_modes_for_target` broke after `TC003` moved
  `DeployTarget` behind `TYPE_CHECKING`; the doctest now imports it directly so it
  stays runnable outside type-checking.

### Changed
- Removed the blanket `[tool.ruff.lint].ignore` list (`RUF002`, `RUF022`,
  `PLC0415`, `TC001`, `TC002`, `TC003`, `TC006`) and fixed every violation at the
  root instead: sorted `__all__` (`RUF022`), moved type-only imports under
  `TYPE_CHECKING` or quoted `cast()` expressions (`TC001`/`TC002`/`TC003`/`TC006`),
  and replaced ambiguous en-dashes in docstrings with ASCII hyphens (`RUF002`).
- Added `[tool.ruff.lint.flake8-type-checking].runtime-evaluated-base-classes`
  for `pydantic.BaseModel` so Pydantic field-type imports stay available at
  runtime instead of being pushed into `TYPE_CHECKING`.
- `PLC0415` (deferred imports): moved trivial deferred imports in
  `adapters/cli/commands/logging.py` and `adapters/cli/main.py` to module top;
  kept the genuine circular-import break in `adapters/cli/root.py` and the
  intentional lazy load of in-memory test adapters in
  `composition/__init__.py`, both now annotated with `# noqa: PLC0415` and a
  reason. Test-only deferred imports are now covered by a `tests/*.py`
  per-file-ignore instead of being fixed one by one.

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
