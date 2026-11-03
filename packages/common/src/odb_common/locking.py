"""Chave de lock de escrita por tabela, compartilhada entre lakehouse e catálogo."""

from __future__ import annotations

import hashlib


class LockUnavailableError(RuntimeError):
    """Outro escritor detém o lock da tabela."""


def lock_key(table_uri: str) -> int:
    """Chave estável de 64 bits com sinal (faixa do ``bigint`` do PostgreSQL)."""
    digest = hashlib.sha256(b"odb.table-write:" + table_uri.rstrip("/").encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)
