#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

CONFIG_FILE="${PYRIGHT_CONFIG:-pyrightconfig.json}"
if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "pyright config not found: ${CONFIG_FILE}" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -n "${PYRIGHT_BIN:-}" ]]; then
  PYRIGHT_CMD=("${PYRIGHT_BIN}")
elif command -v pyright >/dev/null 2>&1; then
  PYRIGHT_CMD=("$(command -v pyright)")
elif "${PYTHON_BIN}" -m pyright --version >/dev/null 2>&1; then
  PYRIGHT_CMD=("${PYTHON_BIN}" -m pyright)
else
  echo "pyright executable not found." >&2
  echo "Install development tools with: make install-dev" >&2
  echo "Or set PYRIGHT_BIN to a specific Pyright executable path." >&2
  exit 127
fi

echo "Running: ${PYRIGHT_CMD[*]} --project ${CONFIG_FILE} $*"
exec "${PYRIGHT_CMD[@]}" --project "${CONFIG_FILE}" "$@"
