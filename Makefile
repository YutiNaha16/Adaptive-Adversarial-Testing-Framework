# Adaptive Adversarial Testing Framework — task surface (Feature F01 / Epic E0).
# Single discoverable home for project commands. Run `make` or `make help` for the list.

PYTHON ?= python3.12
VENV   := .venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

.DEFAULT_GOAL := help
.PHONY: help setup lock test run lint lab-up lab-down lab-check lab-status lab-smoke demo demo-live dashboard lab-traffic lab-baseline transferability

COMPOSE := docker compose -f lab/docker-compose.yml

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
	$(VENV)/bin/pip-compile --generate-hashes --allow-unsafe --extra-index-url https://download.pytorch.org/whl/cpu --output-file=requirements.txt requirements.in

test:  ## Run the test suite (pytest); non-zero exit on failure
	$(PY) -m pytest

lint:  ## Check lint + formatting (ruff); non-zero exit on any violation
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

run:  ## Run the full experiment end-to-end (requires: make setup; optionally: make lab-up)
	$(PY) src/run_experiment.py

lab-up:  ## Build/pull images and start the isolated lab (internal-only network)
	$(COMPOSE) build
	$(COMPOSE) up -d

lab-down:  ## Stop and remove all lab containers, the lab network, and eve volume
	$(COMPOSE) down --volumes --remove-orphans
	@docker rm -f aatf-attacker aatf-defender aatf-environment aatf-suricata 2>/dev/null; true
	@docker volume rm aatf-eve 2>/dev/null; true

lab-check:  ## Verify lab has no outbound internet access (exits 1 on breach)
	@bash lab/scripts/check-isolation.sh

lab-status:  ## Show current lab container states (exits 0=running, 1=stopped, 2=degraded)
	@bash lab/scripts/lab-status.sh

lab-smoke:  ## Send smoke probe; verify ET Open SID fires in eve.json (exits 1 on failure)
	@bash lab/scripts/lab-smoke.sh

demo:  ## BH demo: replay stored Round 1/2/3 results (~5 s, no Docker needed)
	$(PY) src/demo.py

demo-live:  ## BH demo: run 5 real episodes with ParameterizedDQN (~30 s, no Docker)
	$(PY) src/demo.py --live

lab-traffic:  ## Generate benign HTTP/SSH traffic in the lab (calibrate ML baseline)
	@bash lab/scripts/lab-traffic.sh

lab-baseline:  ## Capture real benign-traffic feature vectors for IsolationForest training
	$(PY) lab/scripts/capture-baseline.py

dashboard:  ## Start the live metrics dashboard at http://localhost:5050
	@echo "Starting AATF dashboard at http://localhost:5050 ..."
	AATF_OUTPUTS=outputs $(PY) src/dashboard/app.py

transferability:  ## Run two-config transferability test and diff blind spots
	@echo "=== Run A: baseline (config_round3.yaml) ==="
	$(PY) src/run_experiment.py --config config_round3.yaml
	@echo ""
	@echo "=== Run B: alternate ruleset (config_transfer.yaml) ==="
	$(PY) src/run_experiment.py --config config_transfer.yaml
	@echo ""
	@echo "=== Transferability Analysis ==="
	$(PY) lab/scripts/compare-blind-spots.py outputs/run_003 outputs/run_transfer
