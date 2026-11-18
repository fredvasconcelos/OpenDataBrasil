"""Limite de requisições por IP e log estruturado de cada requisição (§18.5, §25)."""

from __future__ import annotations

import ipaddress
import logging
import threading
import time
from collections.abc import Awaitable, Callable, Sequence

from fastapi import Request, Response

from odb_api.errors import error_response

logger = logging.getLogger("odb_api.access")


class RateLimiter:
    """Balde de fichas por cliente: ``per_minute`` requisições, recarga contínua."""

    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        """``per_minute`` = 0 desliga o limite."""
        self._rate = per_minute / 60.0
        self._capacity = float(per_minute)
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        """Consome uma ficha do cliente."""
        if self._capacity <= 0:
            return True
        now = self._clock()
        with self._lock:
            tokens, last = self._buckets.get(client, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * self._rate)
            if len(self._buckets) > 10_000:  # noqa: PLR2004 - teto de memória
                self._buckets.clear()
            if tokens < 1:
                self._buckets[client] = (tokens, now)
                return False
            self._buckets[client] = (tokens - 1, now)
            return True


def client_ip(
    peer: str | None,
    forwarded_for: str | None,
    trusted: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> str:
    """IP do cliente: o último da cadeia ``X-Forwarded-For`` se a conexão vem de um proxy
    confiável; senão, o da própria conexão.

    O último é o que o proxy de borda (Caddy) anotou; os anteriores vêm do cliente e
    podem ser forjados. Valores que não são IP são ignorados.
    """
    if not peer:
        return "unknown"
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    if forwarded_for and any(address in net for net in trusted):
        last = forwarded_for.split(",")[-1].strip()
        try:
            return str(ipaddress.ip_address(last))
        except ValueError:
            return peer
    return peer


def make_middleware(
    limiter: RateLimiter,
    trusted_proxies: Sequence[str] = (),
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Middleware HTTP: limite por cliente (exceto ``/health``) e log de acesso."""
    trusted = [ipaddress.ip_network(cidr, strict=False) for cidr in trusted_proxies]

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        client = client_ip(
            request.client.host if request.client else None,
            request.headers.get("x-forwarded-for"),
            trusted,
        )
        if request.url.path != "/health" and not limiter.allow(client):
            response: Response = error_response(429, "rate_limited", "limite de requisições")
        else:
            response = await call_next(request)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "release_id": response.headers.get("x-odb-release"),
            },
        )
        return response

    return middleware
