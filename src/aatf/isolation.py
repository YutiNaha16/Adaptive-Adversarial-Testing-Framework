from __future__ import annotations

import ipaddress
import socket

LAB_NETWORKS_DEFAULT: list[str] = ["172.28.0.0/16"]

_LOOPBACK_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]


class ExternalTargetError(ValueError):
    """Raised when a target is not within the permitted lab network or loopback."""

    def __init__(self, target: str, reason: str) -> None:
        self.target = target
        self.reason = reason
        super().__init__(f"External target rejected — {target}: {reason}")


def assert_lab_internal(
    target: str,
    allowed_networks: list[str] | None = None,
) -> None:
    """Raise ExternalTargetError if target is not lab-internal or loopback.

    Args:
        target: IP address string or hostname to validate.
        allowed_networks: CIDR strings of permitted networks.
            Defaults to LAB_NETWORKS_DEFAULT (172.28.0.0/16).
            Loopback is always permitted regardless of this parameter.

    Raises:
        ExternalTargetError: if the target is outside all permitted networks.
    """
    nets = [
        ipaddress.ip_network(n, strict=False) for n in (allowed_networks or LAB_NETWORKS_DEFAULT)
    ]

    try:
        addr = ipaddress.ip_address(target)
        _check_address(addr, target, nets)
    except ValueError:
        # Not a bare IP — treat as hostname; resolve and check all addresses.
        try:
            results = socket.getaddrinfo(target, None)
        except socket.gaierror as exc:
            raise ExternalTargetError(
                target, f"hostname resolution failed — failing closed: {exc}"
            ) from exc
        for _family, _type, _proto, _canonname, sockaddr in results:
            addr = ipaddress.ip_address(sockaddr[0])
            _check_address(addr, target, nets)


def _check_address(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
    target: str,
    allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> None:
    if any(addr in lb for lb in _LOOPBACK_NETWORKS):
        return
    if any(addr in net for net in allowed_networks):
        return
    raise ExternalTargetError(
        target,
        f"{addr} is not within permitted lab networks {[str(n) for n in allowed_networks]}",
    )
