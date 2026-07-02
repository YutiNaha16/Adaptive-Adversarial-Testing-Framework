# Adaptive Adversarial Testing Framework — task surface (Feature F01 / Epic E0).
# Single discoverable home for project commands. Run `make` or `make help` for the list.

PYTHON ?= python3.12
VENV   := .venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

.DEFAULT_GOAL := help
.PHONY: help setup lock test run lint

help:  ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

setup:  ## Create/refresh .venv and install pinned, hashed deps + the package (editable)
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install --require-hashes -r requirements.txt
	$(PIP) install -e . --no-deps
	@echo "Setup complete. Tools live in $(VENV)/bin (no activation needed via make)."

lock:  ## Recompile requirements.txt from requirements.in (fully pinned + hashed)
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip pip-tools
	$(VENV)/bin/pip-compile --generate-hashes --allow-unsafe --output-file=requirements.txt requirements.in

test:  ## Run the test suite (pytest); non-zero exit on failure
	$(PY) -m pytest

lint:  ## Check lint + formatting (ruff); non-zero exit on any violation
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

run:  ## Run the experiment entrypoint (stub)
	$(PY) -m aatf
