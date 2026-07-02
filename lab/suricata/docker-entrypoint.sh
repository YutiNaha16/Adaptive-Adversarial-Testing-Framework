#!/usr/bin/env sh
# Suricata entrypoint: waits for aatf-lab-br, translates disabled.conf →
# threshold.conf suppress entries, then exec's Suricata.
set -e

DISABLED_CONF="/lab-rules/disabled.conf"
THRESHOLD_CONF="/etc/suricata/threshold.conf"

# Wait up to 30s for the Docker bridge interface to appear on the host
i=0
while ! ip link show aatf-lab-br > /dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        echo "ERROR: aatf-lab-br not available after 30s — is the lab network up?" >&2
        exit 1
    fi
    echo "Waiting for aatf-lab-br (${i}/30)..."
    sleep 1
done
echo "aatf-lab-br is up."

# Generate threshold.conf from disabled.conf (empty file = no suppression)
printf '' > "$THRESHOLD_CONF"
if [ -f "$DISABLED_CONF" ]; then
    while IFS= read -r line; do
        # Strip leading/trailing whitespace
        line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        # Skip blank lines and comment lines
        case "$line" in
            ''|\#*) continue ;;
        esac
        printf 'suppress gen_id 1, sig_id %s\n' "$line" \
            >> "$THRESHOLD_CONF"
        echo "Suppressing SID: $line"
    done < "$DISABLED_CONF"
fi

echo "Starting Suricata on interface aatf-lab-br..."
exec suricata \
    -c /etc/suricata/suricata.yaml \
    --af-packet=aatf-lab-br \
    -l /var/log/suricata/
