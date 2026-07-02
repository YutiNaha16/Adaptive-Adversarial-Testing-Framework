#!/usr/bin/env sh
# Report lab state: exits 0=running, 1=stopped, 2=degraded.

CONTAINERS="aatf-attacker aatf-defender aatf-environment"
running=0
total=0

for name in $CONTAINERS; do
    total=$((total + 1))
    state=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || echo "absent")
    printf '  %-22s %s\n' "$name" "$state"
    if [ "$state" = "running" ]; then
        running=$((running + 1))
    fi
done

if [ "$running" -eq "$total" ]; then
    printf 'Lab state: running (%d/%d containers up)\n' "$running" "$total"
    exit 0
elif [ "$running" -eq 0 ]; then
    printf 'Lab state: stopped (0/%d containers up)\n' "$total"
    exit 1
else
    printf 'Lab state: degraded (%d/%d containers up)\n' "$running" "$total"
    exit 2
fi
