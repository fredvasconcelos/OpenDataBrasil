"""Cache de respostas por release (plano R-V, achado de carga da V5).

As respostas de mapa, série, detalhe, tabela e territórios dependem só do release e da
URL. A chave inclui o release ativo, então a troca de release (ou um rollback) nunca
serve dado de outro release (§17.4). O cache é por processo, em memória, com teto em
bytes e descarte do menos usado. Desligado por padrão (``ODB_API_RESPONSE_CACHE_MB=0``).
"""

from __future__ import annotations

import re
import threading
from collections import OrderedDict
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

CACHEABLE = re.compile(
    r"^/api/v1/(kpis/[a-z0-9_]+/(map|series|detail|details|table|pivot|history)|geographies(/[^/]+)?)$"
)
# Bloco de contas (ADR-0037): chave com o release do escopo ``contas``.
CONTAS_CACHEABLE = re.compile(
    r"^/api/v1/contas/(meta|map|composition|series|ranking|table|busca|execucao"
    r"|favorecidos/[0-9a-f]{16})$"
)
_OK = 200
_PIVOT_REFUSAL = 422
# x-robots-tag: as fichas de pessoa física não são indexadas (ADR-0031, 5.6).
_KEEP_HEADERS = (
    "content-type",
    "x-odb-release",
    "etag",
    "cache-control",
    "content-disposition",
    "x-robots-tag",
)

Key = tuple[str, str, str]
Entry = tuple[bytes, dict[str, str], int]


class ResponseCache:
    """LRU de corpos de resposta com teto em bytes (seguro entre threads)."""

    def __init__(self, max_bytes: int) -> None:
        """``max_bytes`` = 0 desliga o cache."""
        self._max = max_bytes
        self._size = 0
        self._items: OrderedDict[Key, Entry] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @property
    def enabled(self) -> bool:
        """Há espaço configurado?"""
        return self._max > 0

    def get(self, key: Key) -> Entry | None:
        """Resposta guardada (e a marca como recém-usada)."""
        with self._lock:
            found = self._items.get(key)
            if found is None:
                self.misses += 1
                return None
            self._items.move_to_end(key)
            self.hits += 1
            return found

    def put(self, key: Key, body: bytes, headers: dict[str, str], status: int = _OK) -> None:
        """Guarda a resposta, descartando as menos usadas até caber."""
        if len(body) > self._max // 4:  # uma resposta enorme não expulsa o cache inteiro
            return
        with self._lock:
            old = self._items.pop(key, None)
            if old is not None:
                self._size -= len(old[0])
            self._items[key] = (body, headers, status)
            self._size += len(body)
            while self._size > self._max and self._items:
                _, (dropped, _, _) = self._items.popitem(last=False)
                self._size -= len(dropped)


def make_cache_middleware(
    cache: ResponseCache,
    current_release: Callable[[], str | None],
    *,
    contas_release: Callable[[], str | None] | None = None,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Middleware: serve do cache os GET cacheáveis do release ativo.

    As rotas das contas usam o release do próprio escopo (``contas_release``).
    """

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        resolve = current_release
        if contas_release is not None and CONTAS_CACHEABLE.match(path):
            resolve = contas_release
        elif not CACHEABLE.match(path):
            return await call_next(request)
        if not cache.enabled or request.method != "GET":
            return await call_next(request)
        try:
            release = resolve()
        except Exception:  # sem release, a própria rota responde o erro adequado
            release = None
        if release is None:
            return await call_next(request)
        key = (release, path, request.url.query)
        found = cache.get(key)
        if found is not None:
            body, headers, status = found
            return Response(body, status_code=status, headers={**headers, "X-ODB-Cache": "hit"})
        response = await call_next(request)
        cacheable_status = response.status_code == _OK or (
            response.status_code == _PIVOT_REFUSAL and path.endswith("/pivot")
        )
        if not cacheable_status or response.headers.get("x-odb-release") != release:
            return response
        chunks = [chunk async for chunk in response.body_iterator]  # type: ignore[attr-defined]
        body = b"".join(c if isinstance(c, bytes) else c.encode() for c in chunks)
        headers = {k: v for k, v in response.headers.items() if k.lower() in _KEEP_HEADERS}
        cache.put(key, body, headers, response.status_code)
        return Response(
            body, status_code=response.status_code, headers={**headers, "X-ODB-Cache": "miss"}
        )

    return middleware
