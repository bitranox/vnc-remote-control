# Installation Guide

> The CLI is built on rich-click. OCR additionally needs the `tesseract` system binary (see below).

This guide collects every supported method to install `vnc_remote_control`, including
isolated environments and system package managers. Pick the option that matches your workflow.


## System prerequisites

tesseract is a required system dependency. OCR is core to the tool (the `ocr` and
`click-text` commands use it), so install tesseract before the package:

```bash
# Debian/Ubuntu
sudo apt-get install tesseract-ocr
# macOS
brew install tesseract
# Windows
choco install tesseract
```


## We recommend `uv` to install the package

### `uv` = Ultra-fast Python package manager

> lightning-fast replacement for `pip`, `venv`, `pip-tools`, and `poetry`
written in Rust, compatible with PEP 621 (`pyproject.toml`)

### `uvx` = On-demand tool runner

> runs tools temporarily in isolated environments without installing them globally


## Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## One-shot run via uvx (no install needed)

```bash
uvx vnc_remote_control@latest --help
```

## Persistent install as CLI tool

```bash
# install the CLI tool (isolated environment, added to PATH)
uv tool install vnc_remote_control

# upgrade to latest
uv tool upgrade vnc_remote_control
```

## Install as project dependency

```bash
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
uv pip install vnc_remote_control
```

## Verify installation

After any install method, confirm the CLI is available:

```bash
vnc-remote-control --version
```

---

## Installation via pip

```bash
# optional, install in a venv (recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
# install from PyPI
pip install vnc_remote_control
# optional install from GitHub
pip install "git+https://github.com/bitranox/vnc-remote-control"
# optional development install from local
pip install -e ".[dev]"
# optional install from local runtime only:
pip install .
```

## Per-User Installation (No Virtualenv) - from local

```bash
# install from PyPI
pip install --user vnc_remote_control
# optional install from GitHub
pip install --user "git+https://github.com/bitranox/vnc-remote-control"
# optional install from local
pip install --user .
```

> Note: This respects PEP 668. Avoid using it on system Python builds marked as
> "externally managed". Ensure `~/.local/bin` (POSIX) is on your PATH so the CLI is available.

## pipx (Isolated CLI-Friendly Environment)

```bash
# install pipx via pip
python -m pip install pipx
# optional install pipx via apt
sudo apt install python-pipx
# install via pipx from PyPI
pipx install vnc_remote_control
# optional install via pipx from GitHub
pipx install "git+https://github.com/bitranox/vnc-remote-control"
# optional install from local
pipx install .
pipx upgrade vnc_remote_control
# install from Git tag
pipx install "git+https://github.com/bitranox/vnc-remote-control@v1.1.0"
```

## From Build Artifacts

```bash
python -m build
pip install dist/vnc_remote_control-*.whl
pip install dist/vnc_remote_control-*.tar.gz   # sdist
```

## Poetry or PDM Managed Environments

```bash
# Poetry
poetry add vnc_remote_control     # as dependency
poetry install                          # for local dev

# PDM
pdm add vnc_remote_control
pdm install
```

## Install Directly from Git

```bash
pip install "git+https://github.com/bitranox/vnc-remote-control"
```

## System Package Managers (Optional Distribution Channels)

- Use [fpm](https://fpm.readthedocs.io/) to repackage the Python wheel into `.deb` or `.rpm` for distribution via `apt` or `yum`/`dnf`.

All methods register both the `vnc_remote_control` and
`vnc-remote-control` commands on your PATH.
