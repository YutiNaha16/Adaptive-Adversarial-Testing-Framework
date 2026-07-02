# Data Model: 004-e1-docker-lab

F04 is infrastructure — no Python data types or Pydantic models. The "data model" here
describes the configuration entities that define the lab and the states it transitions through.

---

## Lab Network

Defined in `lab/docker-compose.yml` under `networks:`.

| Field | Value | Notes |
|-------|-------|-------|
| `name` | `aatf-lab` | Fixed, deterministic (D6) |
| `internal` | `true` | Constitution Principle I — mandatory |
| `subnet` | `172.28.0.0/16` | Non-conflicting private range (D6) |
| gateway | absent | `internal: true` removes default gateway |

---

## Container (Stub)

Three instances: attacker, defender, environment. All identical at this stage.

| Field | Value | Notes |
|-------|-------|-------|
| `image` | `alpine:3.19` | Pinned tag — reproducibility (D2) |
| `container_name` | `aatf-<role>` | Deterministic — FR-009 (D6) |
| `networks` | `[aatf-lab]` | Internal-only network only |
| `command` | idle sleep loop | Stub — no experiment logic |
| `restart` | `no` | Explicit: stubs must not auto-restart |

---

## Lab State

The aggregate state of the lab as reported by `make lab-status`.

| State | Condition |
|-------|-----------|
| `running` | All 3 containers in `running` status |
| `stopped` | No containers exist or all are stopped |
| `degraded` | ≥1 container exited unexpectedly while others run |

---

## Isolation Check Result

The output of `make lab-check` / `lab/scripts/check-isolation.sh`.

| Field | Values | Notes |
|-------|--------|-------|
| `outcome` | `isolated` \| `breach` \| `error` | — |
| `target` | `8.8.8.8:53` | Fixed external probe target (D3) |
| `timeout_s` | `5` | Safety net; failure is typically instant (D3) |
| `exit_code` | `0` = isolated, `1` = breach, `2` = lab not running | FR-005 |
| `message` | Human-readable line to stdout/stderr | — |

---

## State Transitions

```
[no lab]  --make lab-up-->  [running]
[running] --make lab-down-> [no lab]
[running] --container exit-> [degraded]
[degraded] --make lab-down-> [no lab]
[degraded] --make lab-up-->  [running]  (idempotent recreate)
```
