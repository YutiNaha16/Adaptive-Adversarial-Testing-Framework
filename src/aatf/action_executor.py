"""Action executor — translates Action objects into defanged lab-only network traffic."""

from __future__ import annotations

import ipaddress
import random
import socket
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass

from aatf.contracts import Action

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

SendFn = Callable[[str, int, bytes], None]
SleepFn = Callable[[float], None]
HandlerFn = Callable[[Action, random.Random, SendFn, SleepFn], int]

# ---------------------------------------------------------------------------
# Lab network
# ---------------------------------------------------------------------------

_LAB_NETWORK = ipaddress.ip_network("172.28.0.0/16")

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ExternalTargetError(ValueError):
    def __init__(self, ip: str) -> None:
        super().__init__(f"target_ip {ip!r} is outside lab network 172.28.0.0/16")


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    action_id: str
    category: str
    success: bool
    emitted_count: int
    error: str | None = None


# ---------------------------------------------------------------------------
# Default send function (production — real sockets, silences OSError)
# ---------------------------------------------------------------------------


def _default_send_fn(host: str, port: int, payload: bytes) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            sock.connect_ex((host, port))
            try:
                sock.sendall(payload)
            except OSError:
                pass
    except OSError:
        pass


def _default_udp_send_fn(host: str, port: int, payload: bytes) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.5)
            sock.sendto(payload, (host, port))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Handlers — scan category
# ---------------------------------------------------------------------------


def _handle_tcp_port_scan(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port_range = action.parameters.get("port_range", "1-1024")
    timing_ms = float(action.parameters.get("timing_ms", 0))
    start_str, end_str = port_range.split("-")
    start, end = int(start_str), int(end_str)
    count = 0
    for port in range(start, end + 1):
        send_fn(target, port, b"SYN")
        count += 1
        if timing_ms > 0:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return max(1, count)


def _handle_udp_sweep(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port_range = action.parameters.get("port_range", "1-1024")
    timing_ms = float(action.parameters.get("timing_ms", 0))
    start_str, end_str = port_range.split("-")
    start, end = int(start_str), int(end_str)
    count = 0
    for port in range(start, end + 1):
        send_fn(target, port, b"UDP")
        count += 1
        if timing_ms > 0:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return max(1, count)


def _handle_icmp_ping_sweep(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    rate_pps = max(1, int(action.parameters.get("rate_pps", 1)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    for i in range(rate_pps):
        send_fn(target, 7, b"PING")
        if timing_ms > 0 and i < rate_pps - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return rate_pps


# ---------------------------------------------------------------------------
# Handlers — brute category
# ---------------------------------------------------------------------------


def _handle_ssh_brute_force(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 22))
    attempts = max(1, int(action.parameters.get("attempts", 1)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    for i in range(attempts):
        send_fn(target, port, b"SSH-2.0-test\r\n")
        if timing_ms > 0 and i < attempts - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return attempts


def _handle_ftp_brute_force(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 21))
    attempts = max(1, int(action.parameters.get("attempts", 1)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    for i in range(attempts):
        send_fn(target, port, b"USER test\r\nPASS test\r\n")
        if timing_ms > 0 and i < attempts - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return attempts


def _handle_http_basic_brute(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 80))
    attempts = max(1, int(action.parameters.get("attempts", 1)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    payload = b"GET / HTTP/1.1\r\nHost: aatf-defender\r\nAuthorization: Basic dGVzdDp0ZXN0\r\n\r\n"
    for i in range(attempts):
        send_fn(target, port, payload)
        if timing_ms > 0 and i < attempts - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return attempts


# ---------------------------------------------------------------------------
# Handlers — ssh category
# ---------------------------------------------------------------------------


def _handle_ssh_user_enum(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 22))
    usernames = action.parameters.get("usernames", ["root", "admin", "test"])
    timing_ms = float(action.parameters.get("timing_ms", 0))
    count = 0
    for i, username in enumerate(usernames):
        payload = f"SSH-2.0-OpenSSH_7.4 {username}\r\n".encode()
        send_fn(target, port, payload)
        count += 1
        if timing_ms > 0 and i < len(usernames) - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return max(1, count)


def _handle_ssh_version_probe(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 22))
    send_fn(target, port, b"SSH-2.0-OpenSSH_7.4\r\n")
    return 1


# ---------------------------------------------------------------------------
# Handlers — web category
# ---------------------------------------------------------------------------


def _handle_http_dir_scan(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 80))
    wordlist_size = max(1, int(action.parameters.get("wordlist_size", 10)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    paths = [
        "/admin",
        "/config",
        "/backup",
        "/login",
        "/api",
        "/wp-admin",
        "/phpmyadmin",
        "/.env",
        "/secret",
        "/test",
        "/uploads",
        "/static",
        "/assets",
        "/debug",
        "/console",
        "/metrics",
        "/health",
        "/status",
        "/version",
        "/info",
    ]
    count = 0
    for i in range(wordlist_size):
        path = paths[i % len(paths)]
        payload = f"GET {path} HTTP/1.1\r\nHost: aatf-defender\r\n\r\n".encode()
        send_fn(target, port, payload)
        count += 1
        if timing_ms > 0 and i < wordlist_size - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return count


def _handle_http_sqli_probe(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 80))
    rate_rps = max(1, int(action.parameters.get("rate_rps", 1)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    payload = b"GET /?q=1+UNION+SELECT+1-- HTTP/1.1\r\nHost: aatf-defender\r\n\r\n"
    for i in range(rate_rps):
        send_fn(target, port, payload)
        if timing_ms > 0 and i < rate_rps - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return rate_rps


def _handle_http_xss_probe(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 80))
    payload = b"GET /?q=<script>alert(1)</script> HTTP/1.1\r\nHost: aatf-defender\r\n\r\n"
    send_fn(target, port, payload)
    return 1


# ---------------------------------------------------------------------------
# Handlers — dns category
# ---------------------------------------------------------------------------


def _build_dns_query(name: str, qtype: int = 1) -> bytes:
    """Build a minimal DNS wire-format query for the given name and qtype."""
    header = struct.pack(">HHHHHH", 0x1337, 0x0100, 1, 0, 0, 0)
    labels = b""
    for part in name.split("."):
        encoded = part.encode()
        labels += bytes([len(encoded)]) + encoded
    labels += b"\x00"
    question = labels + struct.pack(">HH", qtype, 1)
    return header + question


def _handle_dns_zone_transfer(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    domain = action.parameters.get("domain", "aatf.lab")
    payload = _build_dns_query(domain, qtype=252)  # AXFR = 252
    send_fn(target, 53, payload)
    return 1


def _handle_dns_subdomain_enum(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    domain = action.parameters.get("domain", "aatf.lab")
    wordlist_size = max(1, int(action.parameters.get("wordlist_size", 10)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    subdomains = [
        "mail",
        "www",
        "ftp",
        "vpn",
        "remote",
        "api",
        "dev",
        "staging",
        "test",
        "internal",
        "admin",
        "ns1",
        "ns2",
        "smtp",
        "pop",
        "imap",
        "ldap",
        "db",
        "backup",
        "monitor",
    ]
    count = 0
    for i in range(wordlist_size):
        sub = subdomains[i % len(subdomains)]
        fqdn = f"{sub}.{domain}"
        payload = _build_dns_query(fqdn, qtype=1)  # A record
        send_fn(target, 53, payload)
        count += 1
        if timing_ms > 0 and i < wordlist_size - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return count


# ---------------------------------------------------------------------------
# Handlers — exfil category
# ---------------------------------------------------------------------------


def _handle_dns_exfil(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    chunk_size = max(1, int(action.parameters.get("chunk_size", 16)))
    chunks = max(1, int(action.parameters.get("chunks", 5)))
    timing_ms = float(action.parameters.get("timing_ms", 0))
    count = 0
    for i in range(chunks):
        data = (b"A" * chunk_size).hex()
        label = data[:62]  # DNS label max 63 chars
        fqdn = f"{label}.exfil.aatf.lab"
        payload = _build_dns_query(fqdn, qtype=1)
        send_fn(target, 53, payload)
        count += 1
        if timing_ms > 0 and i < chunks - 1:
            sleep_fn(rng.uniform(0, timing_ms / 1000))
    return count


def _handle_http_exfil(
    action: Action, rng: random.Random, send_fn: SendFn, sleep_fn: SleepFn
) -> int:
    target = action.parameters.get("target_ip", "172.28.0.2")
    port = int(action.parameters.get("target_port", 80))
    payload_size = max(1, int(action.parameters.get("payload_size", 64)))
    body = b"EXFIL:" + b"X" * payload_size
    request = (
        b"POST /upload HTTP/1.1\r\n"
        b"Host: aatf-defender\r\n"
        b"Content-Type: application/octet-stream\r\n"
        + f"Content-Length: {len(body)}\r\n".encode()
        + b"\r\n"
        + body
    )
    send_fn(target, port, request)
    return 1


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

_HANDLERS: dict[str, HandlerFn] = {
    "tcp_port_scan": _handle_tcp_port_scan,
    "udp_sweep": _handle_udp_sweep,
    "icmp_ping_sweep": _handle_icmp_ping_sweep,
    "ssh_brute_force": _handle_ssh_brute_force,
    "ftp_brute_force": _handle_ftp_brute_force,
    "http_basic_brute": _handle_http_basic_brute,
    "ssh_user_enum": _handle_ssh_user_enum,
    "ssh_version_probe": _handle_ssh_version_probe,
    "http_dir_scan": _handle_http_dir_scan,
    "http_sqli_probe": _handle_http_sqli_probe,
    "http_xss_probe": _handle_http_xss_probe,
    "dns_zone_transfer": _handle_dns_zone_transfer,
    "dns_subdomain_enum": _handle_dns_subdomain_enum,
    "dns_exfil": _handle_dns_exfil,
    "http_exfil": _handle_http_exfil,
}


# ---------------------------------------------------------------------------
# ActionExecutor
# ---------------------------------------------------------------------------


class ActionExecutor:
    def __init__(
        self,
        seed: int,
        send_fn: SendFn | None = None,
        sleep_fn: SleepFn | None = None,
    ) -> None:
        self._rng = random.Random(seed)
        self._send_fn: SendFn = send_fn if send_fn is not None else _default_send_fn
        self._sleep_fn: SleepFn = sleep_fn if sleep_fn is not None else time.sleep
        self._handlers: dict[str, HandlerFn] = dict(_HANDLERS)

    def execute(self, action: Action) -> ExecutionResult:
        target_ip = action.parameters.get("target_ip", "172.28.0.2")
        try:
            addr = ipaddress.ip_address(target_ip)
        except ValueError:
            raise ExternalTargetError(target_ip) from None
        if addr not in _LAB_NETWORK:
            raise ExternalTargetError(target_ip)

        handler = self._handlers.get(action.action_id)
        if handler is None:
            return ExecutionResult(
                action_id=action.action_id,
                category=action.category,
                success=False,
                emitted_count=0,
                error=f"no handler for {action.action_id!r}",
            )

        try:
            count = handler(action, self._rng, self._send_fn, self._sleep_fn)
            return ExecutionResult(
                action_id=action.action_id,
                category=action.category,
                success=True,
                emitted_count=max(1, count),
            )
        except Exception as exc:
            return ExecutionResult(
                action_id=action.action_id,
                category=action.category,
                success=False,
                emitted_count=0,
                error=str(exc),
            )
