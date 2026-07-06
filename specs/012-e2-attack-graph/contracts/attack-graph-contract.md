# Attack Graph Contracts (F09)

## C-001 — Entry-point actions available with empty completed set

`ATTACK_GRAPH.available_actions(set())` returns a list containing exactly
`{"tcp_port_scan", "udp_sweep", "icmp_ping_sweep", "dns_subdomain_enum"}` — 4 ids, no more.

---

## C-002 — No non-entry-point in empty-completed result

`set(ATTACK_GRAPH.available_actions(set()))` is a subset of the 4 entry-point ids;
no successor action_id (e.g. `"ssh_brute_force"`) appears.

---

## C-003 — Completing tcp_port_scan unlocks its successors

`ATTACK_GRAPH.available_actions({"tcp_port_scan"})` contains all of:
`ssh_brute_force`, `ftp_brute_force`, `http_dir_scan`, `ssh_user_enum`
(in addition to the 4 entry-points).

---

## C-004 — Completing dns_subdomain_enum unlocks dns_zone_transfer

`ATTACK_GRAPH.available_actions({"dns_subdomain_enum"})` contains `"dns_zone_transfer"`.

---

## C-005 — Completing http_sqli_probe unlocks http_exfil

`ATTACK_GRAPH.available_actions({"http_sqli_probe"})` contains `"http_exfil"`.

---

## C-006 — Completing dns_zone_transfer unlocks dns_exfil

`ATTACK_GRAPH.available_actions({"dns_zone_transfer"})` contains `"dns_exfil"`.

---

## C-007 — All 15 actions available when all 15 completed

`set(ATTACK_GRAPH.available_actions({defn.action_id for defn in REGISTRY.list_actions()}))
== {defn.action_id for defn in REGISTRY.list_actions()}` — all 15 ids returned.

---

## C-008 — Unknown action_id in completed is silently ignored

`ATTACK_GRAPH.available_actions({"nonexistent_action_xyz"})` does NOT raise;
returns the same result as `available_actions(set())`.

---

## C-009 — Import-time validation: unknown action_id raises ValueError

Constructing `AttackGraph(entry_points=frozenset({"unknown_id"}), edges={})` raises `ValueError`
with the unknown id in the message.

---

## C-010 — available_actions is non-destructive (idempotent)

Calling `available_actions({"tcp_port_scan"})` twice on the same instance returns
identical results both times — no mutation of internal state.

---

## C-011 — available_actions result is sorted

`ATTACK_GRAPH.available_actions(set())` returns a list in ascending lexicographic order
(i.e. `result == sorted(result)`).

---

## C-012 — ATTACK_GRAPH is accessible as a module-level constant

`from aatf.attack_graph import ATTACK_GRAPH` succeeds without calling any constructor;
`isinstance(ATTACK_GRAPH, AttackGraph)` is True.
