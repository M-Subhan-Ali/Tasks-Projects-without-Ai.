"""Keep webhooks away from internal addresses (SSRF protection).

The API itself sends the webhook POST, from inside our network. Without these
checks an admin could register http://localhost:5432, http://192.168.1.10 or
http://169.254.169.254 (cloud metadata) and make the server talk to machines
that the outside world can't reach. That is Server-Side Request Forgery (SSRF).

Checking the URL once, when the webhook is registered, is not enough:
- a hostname can resolve to a private IP (internal.example.com -> 10.0.0.5);
- DNS can change after registration ("DNS rebinding"): public when checked,
  127.0.0.1 when we connect;
- a receiver can answer with a redirect to an internal address.

So the checks run in three places:
1. schemas.py, at registration: IP literals and localhost names (no DNS);
2. webhook_service.py, at registration: the hostname is resolved and every
   address it resolves to must be public;
3. safe_http.py, on EVERY connection: the host is resolved again, every address
   is checked, and the socket connects to the checked IP itself, so there is no
   second lookup that could give a different answer. Redirects are not followed.

ALLOW_LOCAL_WEBHOOKS=true (local development only) allows loopback, i.e.
localhost, 127.0.0.0/8 and ::1, so the demo receiver on localhost:9000 works.
Private and link-local addresses stay blocked even then.
"""

import ipaddress
import socket

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

# NAT64: an IPv6 address in 64:ff9b::/96 carries an IPv4 address in its last
# 32 bits, and a NAT64 gateway forwards it there. Python calls these "global",
# so 64:ff9b::a00:1 (really 10.0.0.1) must be unwrapped and checked as IPv4.
_NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")

LOCAL_HINT = "set ALLOW_LOCAL_WEBHOOKS=true only for local development"


class UnsafeDestination(ValueError):
    """The URL, or an address its host resolves to, may not receive webhooks.

    A ValueError, so Pydantic validators can raise it straight away (→ 422).
    """


def _unwrap_ipv4(ip: IPAddress) -> IPAddress:
    """Return the IPv4 address hidden inside an IPv6 one, if there is one.

    ::ffff:127.0.0.1 (IPv4-mapped) reaches 127.0.0.1, so it must be judged as 127.0.0.1.
    """
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return ip.ipv4_mapped
        if ip in _NAT64_PREFIX:
            return ipaddress.IPv4Address(int(ip) & 0xFFFF_FFFF)
    return ip


def check_ip(ip: IPAddress, allow_local: bool) -> None:
    """Raise UnsafeDestination unless webhooks may be sent to this address.

    The order matters: Python counts 127.0.0.1 and 169.254.x.x as "private"
    too, so loopback and link-local are checked first to get the right reason.
    """
    ip = _unwrap_ipv4(ip)

    if ip.is_loopback:  # 127.0.0.0/8, ::1
        if allow_local:
            return
        raise UnsafeDestination(f"{ip} is a loopback address ({LOCAL_HINT})")
    if ip.is_link_local:  # 169.254.0.0/16 (cloud metadata), fe80::/10
        raise UnsafeDestination(f"{ip} is a link-local address")
    if ip.is_private:  # 10/8, 172.16/12, 192.168/16, fc00::/7, 0.0.0.0/8, ...
        raise UnsafeDestination(f"{ip} is a private address")
    # Anything else that isn't a normal internet address: multicast (which
    # Python calls "global"), 100.64.0.0/10 (carrier-grade NAT), reserved...
    if ip.is_multicast or not ip.is_global:
        raise UnsafeDestination(f"{ip} is not a public internet address")


def parse_ip(host: str) -> IPAddress | None:
    """The host as an IP address, or None if it is a hostname. Accepts "[::1]"."""
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


def is_local_hostname(host: str) -> bool:
    # "localhost." (trailing dot) is the same name. Every *.localhost name
    # points at this machine too (RFC 6761).
    name = host.rstrip(".").lower()
    return name == "localhost" or name.endswith(".localhost")


def check_host(host: str, allow_local: bool) -> None:
    """The checks that need no DNS lookup: IP literals and localhost names."""
    ip = parse_ip(host)
    if ip is not None:
        check_ip(ip, allow_local)
    elif is_local_hostname(host) and not allow_local:
        raise UnsafeDestination(f"localhost is not allowed ({LOCAL_HINT})")


def resolve(host: str, port: int) -> list[IPAddress]:
    """Every address the host resolves to (tests replace this with a fake DNS)."""
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    # info[4] is the socket address; its first item is the IP as text.
    return list(dict.fromkeys(ipaddress.ip_address(info[4][0]) for info in infos))


def resolve_safe(host: str, port: int, allow_local: bool) -> list[IPAddress]:
    """Resolve the host and return its addresses, if EVERY one of them is safe.

    All of them, not just the first: a hostname with one public and one private
    record could otherwise get us connected to the private one.
    """
    check_host(host, allow_local)

    ip = parse_ip(host)
    if ip is not None:
        return [ip]

    try:
        addresses = resolve(host, port)
    except OSError as error:  # socket.gaierror: no such host, DNS down...
        raise UnsafeDestination(f"could not resolve host {host!r}") from error
    if not addresses:
        raise UnsafeDestination(f"could not resolve host {host!r}")

    for address in addresses:
        check_ip(address, allow_local)
    return addresses
