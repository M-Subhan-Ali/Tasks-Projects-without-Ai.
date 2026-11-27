"""An HTTP client that checks the destination IP on every connection it opens.

How a normal client connects: it hands "receiver.example.com" to the OS, the OS
looks it up and connects. We never see which IP it picked, so we can't check it.

This client plugs a GuardedBackend into httpcore2 (the connection layer under
httpx2). Every time a TCP connection is needed, the backend:
1. resolves the hostname itself (url_safety.resolve_safe);
2. refuses if ANY address is loopback / private / link-local / not public;
3. connects to one of the CHECKED IPs, never to the hostname.

Because the IP that was checked is the IP that is used, DNS rebinding (public
when checked, internal a second later) can't slip through. TLS still checks
the certificate against the hostname, because httpcore2 takes the SNI /
server_hostname from the URL, not from the IP we connect to.

Also:
- redirects are never followed (a 3xx counts as a failed delivery), and every
  connection goes through the guard anyway;
- trust_env=False: proxy settings from the environment (HTTP_PROXY...) are
  ignored, because through a proxy the guard would only see the proxy's address.
"""

from collections.abc import Iterable

import httpcore2
import httpx2
from httpcore2 import SOCKET_OPTION

from app import url_safety


class GuardedBackend(httpcore2.NetworkBackend):
    def __init__(self, allow_local: bool, inner: httpcore2.NetworkBackend | None = None) -> None:
        self._allow_local = allow_local
        self._inner = inner if inner is not None else httpcore2.SyncBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> httpcore2.NetworkStream:
        # Raises UnsafeDestination before any socket is opened.
        addresses = url_safety.resolve_safe(host, port, self._allow_local)

        last_error: httpcore2.ConnectError | None = None
        for address in addresses:  # e.g. IPv6 first, then IPv4, like the OS would
            try:
                return self._inner.connect_tcp(
                    str(address), port, timeout, local_address, socket_options
                )
            except httpcore2.ConnectError as error:
                last_error = error
        assert last_error is not None  # resolve_safe never returns an empty list
        raise last_error

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> httpcore2.NetworkStream:
        raise url_safety.UnsafeDestination("unix sockets are not allowed")

    def sleep(self, seconds: float) -> None:
        self._inner.sleep(seconds)


class GuardedTransport(httpx2.HTTPTransport):
    def __init__(self, allow_local: bool) -> None:
        super().__init__(trust_env=False)
        # HTTPTransport has no option for a custom network backend, so its
        # connection pool is replaced by one that uses the guard. This uses the
        # private `_pool` attribute, which is why httpx2 is pinned to an exact
        # version in requirements.txt; tests/test_webhook_url_safety.py fails
        # if an upgrade ever stops the guard from being used.
        self._pool = httpcore2.ConnectionPool(
            ssl_context=httpx2.create_ssl_context(),
            network_backend=GuardedBackend(allow_local),
        )


def create_guarded_client(timeout: float, allow_local: bool) -> httpx2.Client:
    return httpx2.Client(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
        transport=GuardedTransport(allow_local),
    )
