"""Lock de escrita por tabela via advisory lock de sessão do PostgreSQL.

Implementa estruturalmente ``odb_lakehouse.locking.TableWriteLock``. O lock
pertence a uma conexão dedicada, mantida aberta durante a escrita. Se o processo
morrer, o PostgreSQL libera o lock quando a sessão cai.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, text

from odb_common.locking import LockUnavailableError, lock_key


class PostgresAdvisoryLock:
    """Lock exclusivo, sem espera, por URI de tabela."""

    def __init__(self, engine: Engine) -> None:
        """Usa conexões do engine informado."""
        self._engine = engine

    @contextmanager
    def hold(self, table_uri: str) -> Iterator[None]:
        """Adquire ``pg_try_advisory_lock`` ou lança ``LockUnavailableError``."""
        key = lock_key(table_uri)
        with self._engine.connect() as conn:
            acquired = conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar()
            conn.commit()
            if not acquired:
                msg = f"tabela em escrita por outro processo: {table_uri}"
                raise LockUnavailableError(msg)
            try:
                yield
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
                conn.commit()
