#!/usr/bin/env sh
set -e

TARGET_SID=2001219
TARGET_MSG="ET SCAN Potential SSH Scan"
EVE_PATH="/srv/eve/eve.json"
PROBE_RUNS=6
POLL_TIMEOUT=60
PROBE_INTERVAL=10

if ! docker inspect aatf-attacker > /dev/null 2>&1; then
    echo "ERROR: lab is not running (aatf-attacker absent)" >&2
    exit 1
fi

send_probes() {
    i=0
    while [ "$i" -lt "$PROBE_RUNS" ]; do
        if ! docker exec aatf-attacker nmap -sS -p 22 --min-rate 1000 aatf-defender > /dev/null 2>&1; then
            echo "ERROR: probe failed" >&2
            exit 1
        fi
        i=$((i + 1))
    done
}

echo "Probing aatf-defender (port 22 SYN scan) and polling for SID ${TARGET_SID} in eve.json..."
i=0
while [ "$i" -lt "$POLL_TIMEOUT" ]; do
    # Send a probe batch at t=0 and every PROBE_INTERVAL seconds thereafter
    if [ $((i % PROBE_INTERVAL)) -eq 0 ]; then
        send_probes
    fi
    # Check for alert
    if docker exec aatf-attacker \
        sh -c "grep -q '\"signature_id\":${TARGET_SID}' ${EVE_PATH} 2>/dev/null"; then
        TIMESTAMP=$(docker exec aatf-attacker \
            sh -c "grep '\"signature_id\":${TARGET_SID}' ${EVE_PATH} 2>/dev/null | tail -1" \
            | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4)
        echo "SMOKE PASS: SID ${TARGET_SID} (${TARGET_MSG}) detected at ${TIMESTAMP}"
        exit 0
    fi
    sleep 1
    i=$((i + 1))
done

echo "SMOKE FAIL: SID ${TARGET_SID} not found within ${POLL_TIMEOUT}s" >&2
exit 1
