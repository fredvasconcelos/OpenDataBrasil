"""Contrato do motor SQL de leitura (§11.7).

O contrato não expõe detalhes do DuckDB. A API (Fase 5) monta ``ReadQuery`` a
partir de operações em whitelist e de tabelas resolvidas pelo manifesto de
publicação. Ela nunca repassa SQL ou caminhos recebidos do usuário.

Formato do template: SQL de uma única instrução ``SELECT``/``WITH``, escrito
pela plataforma. As tabelas aparecem como ``{{alias}}`` e os valores como
parâmetros nomeados ``$nome``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

_ALIAS = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class QueryError(RuntimeError):
    """Erro base do motor de consulta."""


class QueryRejectedError(QueryError):
    """Consulta viola as regras de leitura (instrução, tabela ou caminho não permitidos)."""


class QueryTimeoutError(QueryError):
    """Consulta excedeu o tempo limite e foi interrompida."""


class QueryEngineBusyError(QueryError):
    """Limite de consultas simultâneas atingido."""


@dataclass(frozen=True, slots=True)
class PinnedTable:
    """Tabela Delta em versão fixada, normalmente vinda de ``publication.release_table``."""

    table_uri: str
    version: int

    def __post_init__(self) -> None:
        """Rejeita versões negativas."""
        if self.version < 0:
            msg = f"versão inválida: {self.version}"
            raise QueryRejectedError(msg)


@dataclass(frozen=True, slots=True)
class ReadQuery:
    """Consulta controlada sobre tabelas fixadas."""

    sql_template: str
    tables: Mapping[str, PinnedTable]
    params: Mapping[str, Any] = field(default_factory=dict)
    max_rows: int | None = None

    def __post_init__(self) -> None:
        """Valida os aliases das tabelas."""
        bad = [a for a in self.tables if not _ALIAS.fullmatch(a)]
        if bad:
            msg = f"aliases inválidos: {bad}"
            raise QueryRejectedError(msg)


@dataclass(frozen=True, slots=True)
class QueryResult:
    """Resultado tabular com metadados de proveniência."""

    columns: Sequence[str]
    rows: Sequence[tuple[Any, ...]]
    truncated: bool
    elapsed_ms: float
    tables: Mapping[str, PinnedTable]


class ReadEngine(Protocol):
    """Motor SQL somente leitura."""

    def execute(self, query: ReadQuery) -> QueryResult:
        """Executa a consulta aplicando limites de linhas, tempo e concorrência."""
        ...

    def close(self) -> None:
        """Libera recursos."""
        ...
