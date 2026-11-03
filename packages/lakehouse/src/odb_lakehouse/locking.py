"""Contrato de lock de escrita: um escritor por tabela Delta.

O delta-rs resolve conflitos de commit no armazenamento local, mas a plataforma
exige serialização explícita das escritas, o que garante versões previsíveis
para a publicação. A implementação oficial usa advisory lock do PostgreSQL
(``odb_catalog.locks``). Este módulo define o contrato. A chave do lock fica em
``odb_common.locking``.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol

from odb_common.locking import LockUnavailableError, lock_key

__all__ = ["InProcessLock", "LockUnavailableError", "TableWriteLock", "lock_key"]


class TableWriteLock(Protocol):
    """Lock exclusivo por URI de tabela."""

    def hold(self, table_uri: str) -> AbstractContextManager[None]:
        """Adquire o lock da tabela ou lança ``LockUnavailableError``."""
        ...


class InProcessLock:
    """Lock em memória para testes e processos únicos. Não protege entre processos."""

    def __init__(self) -> None:
        """Inicializa o registro de URIs bloqueadas."""
        self._held: set[int] = set()
        self._mutex = threading.Lock()

    @contextmanager
    def hold(self, table_uri: str) -> Iterator[None]:
        """Adquire o lock sem espera; falha se já estiver ocupado."""
        key = lock_key(table_uri)
        with self._mutex:
            if key in self._held:
                msg = f"tabela em escrita por outro processo: {table_uri}"
                raise LockUnavailableError(msg)
            self._held.add(key)
        try:
            yield
        finally:
            with self._mutex:
                self._held.discard(key)
