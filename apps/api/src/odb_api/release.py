"""Release ativo e tabelas fixadas (§17.4, §18.4).

Cada requisição resolve o release uma vez e usa as mesmas versões Delta em
todas as consultas que fizer. O release é relido do PostgreSQL a cada
``ttl_s`` segundos. Assim uma ativação nova vale sem reiniciar a API, e uma
falha do PostgreSQL não derruba consultas por esse intervalo.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from odb_catalog.publication import Release
from odb_query_engine import PinnedTable

logger = logging.getLogger(__name__)


class ReleaseUnavailableError(RuntimeError):
    """Não há release ativo, ou o catálogo está inacessível."""


class TableNotInReleaseError(RuntimeError):
    """Tabela ausente do release resolvido."""


@dataclass(frozen=True, slots=True)
class ReleaseContext:
    """Release resolvido para uma requisição."""

    release: Release

    @property
    def release_id(self) -> str:
        """Identificador do release."""
        return self.release.release_id

    def pinned(self, table_id: str) -> PinnedTable:
        """Tabela Delta na versão do release."""
        table = self.release.tables.get(table_id)
        if table is None:
            msg = f"tabela {table_id} ausente do release {self.release.release_id}"
            raise TableNotInReleaseError(msg)
        return PinnedTable(table.storage_uri, table.delta_version)

    def has(self, table_id: str) -> bool:
        """O release contém a tabela."""
        return table_id in self.release.tables


class ReleaseResolver:
    """Lê o release ativo do escopo, com cache curto."""

    def __init__(
        self,
        load: Callable[[], Release | None],
        *,
        ttl_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """``load`` consulta o PostgreSQL (``PublicationService.active``)."""
        self._load = load
        self._ttl_s = ttl_s
        self._clock = clock
        self._lock = threading.Lock()
        self._cached: Release | None = None
        self._loaded_at = float("-inf")

    def current(self) -> ReleaseContext:
        """Release vigente. Erro se não houver nenhum."""
        with self._lock:
            now = self._clock()
            if self._cached is None or now - self._loaded_at >= self._ttl_s:
                try:
                    release = self._load()
                except Exception as exc:
                    if self._cached is None:
                        msg = "catálogo de publicação inacessível"
                        raise ReleaseUnavailableError(msg) from exc
                    logger.warning(
                        "release lookup failed; using cached release",
                        extra={"release_id": self._cached.release_id},
                    )
                else:
                    if release is None:
                        msg = "nenhum release ativo"
                        raise ReleaseUnavailableError(msg)
                    if self._cached is None or release.release_id != self._cached.release_id:
                        logger.info("active release", extra={"release_id": release.release_id})
                    self._cached = release
                    self._loaded_at = now
            assert self._cached is not None  # noqa: S101 - garantido pelos ramos acima
            return ReleaseContext(self._cached)
