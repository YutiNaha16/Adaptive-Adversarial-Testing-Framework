#!/usr/bin/env bash
# F29 feedback points 7 and 8 — lab reruns.
# 1. C-11 (no N2 cache) and C-12 (+N2 cache) with the fixed DBS/BSP ground-
#    truth logic (explain_double_blind_spots instead of raw explain_evasions).
# 2. A third run with lab/rules/disabled.conf emptied (unmodified ET Open),
#    to check whether natural (non-injected) blind spots exist.
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate

echo "=== [1/3] Lab C-11 rerun (no N2 cache, fixed BSP/DBS logic) ==="
python3 src/run_experiment.py --config config_lab_200_v2.yaml --lab

echo ""
if [ -f outputs/run_lab_200_v2/evasive_cache.npy ]; then
  echo "=== [2/3] Lab C-12 rerun (+N2 cache from run 1) ==="
  python3 src/run_experiment.py --config config_lab_cache_v2.yaml --lab \
    --evasive-cache outputs/run_lab_200_v2/evasive_cache.npy
else
  echo "=== [2/3] SKIPPED — no evasive_cache.npy produced (run 1 found no blind spots) ==="
fi

echo ""
echo "=== [3/3] Point 8 control: unmodified ET Open (disabled.conf emptied) ==="
cp lab/rules/disabled.conf /tmp/disabled.conf.bak
: > lab/rules/disabled.conf
docker compose -f lab/docker-compose.yml restart suricata
sleep 10
bash lab/scripts/lab-smoke.sh || echo "WARNING: lab-smoke check failed, continuing anyway"
python3 src/run_experiment.py --config config_lab_unmodified_etopen.yaml --lab \
  --disabled-conf lab/rules/disabled.conf
cp /tmp/disabled.conf.bak lab/rules/disabled.conf
docker compose -f lab/docker-compose.yml restart suricata
sleep 10

echo ""
echo "=== DONE ==="
