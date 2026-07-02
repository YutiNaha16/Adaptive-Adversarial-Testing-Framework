#!/usr/bin/env sh
# Verify lab has no outbound internet access.
# Exit 0 = isolated, 1 = breach, 2 = lab not running.
set -e

CONTAINER="aatf-attacker"
TARGET_HOST="8.8.8.8"
TARGET_PORT="53"
TIMEOUT="5"

if ! docker inspect "$CONTAINER" > /dev/null 2>&1; then
    printf 'ERROR: Lab is not running. Run "make lab-up" first.\n' >&2
    exit 2
fi

if docker exec "$CONTAINER" nc -z -w "$TIMEOUT" "$TARGET_HOST" "$TARGET_PORT" 2>/dev/null; then
    printf 'BREACH: Outbound connection to %s:%s succeeded — isolation NOT enforced.\n' \
        "$TARGET_HOST" "$TARGET_PORT" >&2
    exit 1
else
    printf 'ISOLATED: Outbound connection to %s:%s blocked — lab isolation confirmed.\n' \
        "$TARGET_HOST" "$TARGET_PORT"
    exit 0
fi
