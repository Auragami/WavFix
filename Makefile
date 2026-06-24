SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
PYTHONPATH_VALUE ?= src
ARGS ?=
USE_VENV ?= 0
KEEP_BUILD ?= 0

.PHONY: help install install-dev lint format format-check typecheck test check run-gui run-cli build build-pyinstaller build-cxfreeze build-mac clean

define RUN_RUFF
	@RUFF_CMD=""; \
	if [[ -n "$$RUFF_BIN" ]]; then \
		RUFF_CMD="$$RUFF_BIN"; \
	elif command -v ruff >/dev/null 2>&1; then \
		RUFF_CMD="$$(command -v ruff)"; \
	elif $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
		RUFF_CMD="$(PYTHON) -m ruff"; \
	else \
		echo "ruff executable not found."; \
		echo "Install development tools with: make install-dev"; \
		echo "Or set RUFF_BIN to a specific Ruff executable path."; \
		exit 127; \
	fi; \
	eval "$${RUFF_CMD} $(1)"
endef

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "%-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install runtime dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install package with development dependencies
	$(PIP) install -e ".[dev]"

lint: ## Run Ruff lint checks
	$(call RUN_RUFF,check src tests)

format: ## Format Python code with Ruff
	$(call RUN_RUFF,format src tests)

format-check: ## Verify formatting without changing files
	$(call RUN_RUFF,format --check src tests)

typecheck: ## Run Pyright via tools/typecheck.sh
	bash tools/typecheck.sh

test: ## Run unit and smoke tests
	$(PYTHON) -m pytest -q

check: format-check lint typecheck test ## Run formatting + lint + typecheck + tests

run-gui: ## Launch GUI from compatibility entrypoint
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON) src/WavFix.py

run-cli: ## Run CLI (pass ARGS='...')
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON) -m wavfix $(ARGS)

build: build-pyinstaller ## Build the app (default: PyInstaller)

build-pyinstaller: ## Build app with PyInstaller spec (set USE_VENV=1 if needed)
	@if ! $(PYTHON) -m PyInstaller --version >/dev/null 2>&1; then \
		echo "PyInstaller is not installed for $(PYTHON)."; \
		echo "Install it with: $(PIP) install pyinstaller"; \
		exit 1; \
	fi
	USE_VENV=$(USE_VENV) $(PYTHON) -m PyInstaller src/WavFix.spec
	@if [[ "$(KEEP_BUILD)" != "1" ]]; then \
		rm -rf build; \
		echo "Removed PyInstaller intermediate build/ directory."; \
	else \
		echo "Keeping PyInstaller intermediate build/ directory (KEEP_BUILD=1)."; \
	fi
	@echo "PyInstaller build complete."
	@echo "Artifacts are in dist/."

build-cxfreeze: ## Build app with cx_Freeze (macOS: bdist_mac, others: build_exe)
	@if ! $(PYTHON) -c "import cx_Freeze" >/dev/null 2>&1; then \
		echo "cx_Freeze is not installed for $(PYTHON)."; \
		echo "Install it with: $(PIP) install cx_Freeze"; \
		exit 1; \
	fi
	@if [[ "$$(uname -s)" == "Darwin" ]]; then \
		$(PYTHON) src/setup.py bdist_mac; \
	else \
		$(PYTHON) src/setup.py build_exe; \
	fi

build-mac: ## Run existing macOS build script
	bash build_scripts/build_mac.sh

clean: ## Remove local caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .pyright build dist src/__pycache__ src/wavfix/__pycache__ tests/__pycache__
