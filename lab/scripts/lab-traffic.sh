#!/bin/sh
# Generate benign HTTP and SSH traffic in the lab.
# Used to verify real service connectivity and calibrate Suricata baselines.
# Run after `make lab-up`.

set -e

WEB_TARGET="172.28.0.3"
SSH_TARGET="172.28.0.2"
ATTACKER="aatf-attacker"

echo "=== AATF Lab Traffic Generator ==="
echo "Web target : $WEB_TARGET"
echo "SSH target : $SSH_TARGET"
echo ""

# Check attacker container is running
if ! docker inspect "$ATTACKER" >/dev/null 2>&1; then
    echo "ERROR: $ATTACKER not running. Run 'make lab-up' first." >&2
    exit 1
fi

echo "[1/3] Generating benign HTTP traffic (50 requests)..."
docker exec "$ATTACKER" sh -c "
    for i in \$(seq 1 50); do
        wget -q -O /dev/null http://$WEB_TARGET/ 2>/dev/null || true
        wget -q -O /dev/null http://$WEB_TARGET/api/v1/status 2>/dev/null || true
        sleep 0.2
    done
    echo '  HTTP traffic done.'
"

echo "[2/3] Testing SSH reachability (10 probes, no brute force)..."
docker exec "$ATTACKER" sh -c "
    for i in \$(seq 1 10); do
        nc -z -w2 $SSH_TARGET 22 2>/dev/null && echo '  SSH port open.' || echo '  SSH probe $i timed out.'
        sleep 1
    done
" || true

echo "[3/3] Verifying Suricata is capturing traffic..."
if docker inspect aatf-suricata >/dev/null 2>&1; then
    ALERT_COUNT=\$(docker exec aatf-suricata sh -c 'grep -c "\"event_type\":\"alert\"" /var/log/suricata/eve.json 2>/dev/null || echo 0' 2>/dev/null || echo "N/A")
    echo "  Suricata alerts in eve.json: $ALERT_COUNT"
else
    echo "  aatf-suricata not running — skipping alert check."
fi

echo ""
echo "Done. Traffic generation complete."
echo "Benign baseline established — ready for adversarial experiment."
