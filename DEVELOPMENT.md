# Development

## Make Targets

The Makefile is a thin wrapper around the `bmk` tool (installed on demand as a uv
tool). Arguments after the target name are forwarded, so `make test --verbose`
passes `--verbose` through.

| Target | Description |
|--------|-------------|
| `help` | Show the target list (default goal) |
| `install` | Editable install (no dev extras) |
| `dev` | Editable install with dev extras |
| `test` (alias `t`) | Run the test suite with coverage |
| `test-human` (alias `th`) | Run the test suite with human-readable output |
| `testintegration` (aliases `testi`, `ti`) | Run integration tests only |
| `codecov` (aliases `coverage`, `cov`) | Upload the coverage report to Codecov |
| `build` (alias `bld`) | Build wheel and sdist artifacts |
| `clean` (aliases `cln`, `cl`) | Remove build artifacts and caches |
| `run` | Run the project CLI |
| `bump-patch` / `bump-minor` / `bump-major` / `bump` | Bump the version |
| `commit` (alias `c`) | Create a git commit |
| `push` (aliases `psh`, `p`) | Run tests, commit, and push |
| `release` (aliases `rel`, `r`) | Create a versioned release |
| `dependencies` (aliases `deps`, `d`) | Check and list dependencies |
| `dependencies-update` | Update dependencies to latest versions |
| `info` | Print resolved package metadata |
| `version-current` | Print the current version |

## Inner loop

Day to day, run the same checks CI runs, directly:

```bash
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev pyright
uv run --extra dev pytest -q
```

`pytest` runs the doctests in the source modules as well (see
`addopts = ["--doctest-modules"]` in `pyproject.toml`).

The package is standard library only at runtime, so a plain editable install is
enough to run it:

```bash
uv pip install -e .
vnc-remote-control --help
```

The `ocr` and `click-text` subcommands shell out to the external `tesseract`
binary. Install it from your package manager if you want to exercise those paths;
the rest of the CLI works without it.

## Integration tests

Tests that need a live RFB server or tesseract are marked `local_only` and are
skipped in CI. The unit tests mock the client and OCR, so the default run needs
neither a server nor tesseract:

```bash
make test          # all tests except local_only (the CI default)
pytest tests/      # every test, no marker filter
```

To add a test that needs external resources, mark it:

```python
@pytest.mark.local_only
@pytest.mark.os_agnostic
def test_against_a_live_server(...):
    ...
```

## Versioning and metadata

- The single source of truth for the version is `pyproject.toml` (`[project]`).
- The package mirrors its metadata in `src/vnc_remote_control/__init__conf__.py`;
  a test asserts the two versions match.
- Bump the version in both places (or via `make bump`) and add a `CHANGELOG.md`
  entry.

## Dependency auditing

`pip-audit` runs in CI to flag known vulnerabilities. Pin a fixed version in
`[project.optional-dependencies].dev` if a report needs addressing.

## CI and publishing

GitHub Actions workflows:

- `.github/workflows/default_cicd_public.yml`: lint, type-check, test with
  coverage, security scan, build the wheel/sdist, and verify pipx and uv
  installs.
- `.github/workflows/default_release_public.yml`: on a `v*` tag, build the
  artifacts and publish to PyPI when the `PYPI_API_TOKEN` secret is set.

To publish a release:

1. Bump the version in `pyproject.toml` and `__init__conf__.py`, update
   `CHANGELOG.md`.
2. Tag the commit (`git tag v0.1.0 && git push --tags`).
3. Make sure the `PYPI_API_TOKEN` secret is configured in the repo.
