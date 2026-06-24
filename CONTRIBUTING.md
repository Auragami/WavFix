# Contributing to WavFix

Thanks for contributing to WavFix.

## Scope

WavFix focuses on reliable WAV metadata repair for Pioneer DJ compatibility,
with both GUI and CLI workflows powered by the same core logic.

## Development Setup

1. Create and activate a Python `3.11+` virtual environment.
2. Install runtime/build dependencies:

    make install

3. Install development tooling (`pytest`, `ruff`, `pyright`):

    make install-dev

4. Run the quality gate:

    make check

You can also run the tools directly:

    make format-check
    make lint
    make typecheck
    make test

Build the app locally:

    make build

If `ruff` or `pyright` is missing locally, re-run:

    make install-dev

## Running the App

GUI:

    make run-gui

CLI:

    make run-cli ARGS="./tracks --output ./out --batch --overwrite no"

## Project Architecture

- `src/wavfix/core`: File scanning, inspection, output planning, and processing services
- `src/wavfix/ui`: Tkinter UI and controllers
- `src/wavfix/config`: Settings persistence
- `src/wavfix/cli.py`: CLI entrypoint

When adding features, keep business logic in `core` so both GUI and CLI can reuse it.

## Pull Requests

1. Fork the repository and create a feature/fix branch.
2. Keep changes focused and include tests for behavior changes.
3. Ensure `make check` passes.
4. Open a PR with:
   - What changed
   - Why it changed
   - How it was tested

## Reporting Bugs / Requesting Features

- Bugs: <https://github.com/Dreamwalkertunes/WavFix/issues>
- Feature requests: <https://github.com/Dreamwalkertunes/WavFix/issues>

## Code of Conduct

By participating in this project, you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
