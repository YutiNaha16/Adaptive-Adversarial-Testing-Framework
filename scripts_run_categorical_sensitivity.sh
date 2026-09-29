#!/usr/bin/env bash
# F29 feedback point 2 — categorical-encoder sensitivity check.
# Runs IF (bare), IF (+N2 cache), and AE, all under the one-hot/standardized
# CategoricalFeatureEncoder, so we can compare against the MD5-encoding
# results already in the paper (config_round3_ml.yaml / config_round4.yaml).
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate

echo "=== [1/3] Categorical IF (bare, no N2 cache) ==="
python3 src/run_experiment.py --config config_categorical_if.yaml

echo ""
if [ -f outputs/run_categorical_if/evasive_cache.npy ]; then
  echo "=== [2/3] Categorical IF (+N2 cache from run 1) ==="
  python3 src/run_experiment.py --config config_categorical_if_n2.yaml \
    --evasive-cache outputs/run_categorical_if/evasive_cache.npy
else
  echo "=== [2/3] SKIPPED — no evasive_cache.npy produced (run 1 found no blind spots) ==="
fi

echo ""
echo "=== [3/3] Categorical AE ==="
python3 src/run_experiment.py --config config_categorical_ae.yaml

echo ""
echo "=== DONE ==="
