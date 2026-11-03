"""Adaptador DuckDB somente leitura sobre tabelas Delta fixadas.

Defesas em camadas contra escrita e acesso indevido. Nenhuma delas é suficiente
sozinha, porque a extensão Delta do DuckDB consegue escrever via ``ATTACH``
(ver ``tests/contracts/delta_interop``):

1. só uma instrução, do tipo ``SELECT``, classificada pelo parser do DuckDB;
2. as tabelas entram apenas por ``{{alias}}``, resolvido para
   ``delta_scan('<uri>', version => n)``. Não há ``ATTACH``;
3. URIs limitadas às raízes permitidas (Gold por padrão);
4. sandbox do DuckDB: ``enable_external_access=false``, ``allowed_directories``,
   sem auto-instalação nem autoload de extensões e configuração travada;
5. no deploy, o volume Gold é montado ``:ro`` nos serviços de consumo.

Concorrência: uma base DuckDB em memória por instância do motor e um cursor por
consulta, limitado por semáforo. O timeout usa ``cursor.interrupt()``.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb

from odb_common.settings import Settings
from odb_common.storage import StorageError, uri_to_local_path
from odb_query_engine.contract import (
    PinnedTable,
    QueryEngineBusyError,
    QueryRejectedError,
    QueryResult,
    QueryTimeoutError,
    ReadQuery,
)

logger = logging.getLogger(__name__)

_PLACEHOLDER = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")


@dataclass(frozen=True, slots=True)
class DuckDBConfig:
    """Limites de recursos do motor."""

    memory_limit: str = "4GB"
    threads: int = 4
    temp_directory: str = "/lakehouse/tmp/duckdb"
    max_temp_directory_size: str = "20GB"
    timeout_s: float = 30.0
    max_rows: int = 100_000
    max_concurrent: int = 4
    busy_wait_s: float = 5.0
    extension_directory: str | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> DuckDBConfig:
        """Constrói a configuração a partir de ``Settings``."""
        return cls(
            memory_limit=settings.duckdb_memory_limit,
            threads=settings.duckdb_threads,
            temp_directory=settings.duckdb_temp_directory,
            max_temp_directory_size=settings.duckdb_max_temp_directory_size,
            timeout_s=settings.duckdb_query_timeout_s,
            max_rows=settings.duckdb_max_rows,
            max_concurrent=settings.duckdb_max_concurrent_queries,
            extension_directory=settings.duckdb_extension_directory,
        )


def _local_dir(uri_or_path: str) -> str:
    path = uri_to_local_path(uri_or_path) if "://" in uri_or_path else Path(uri_or_path)
    return str(path).rstrip("/") + "/"


class DuckDBReadEngine:
    """Implementação de ``ReadEngine`` com DuckDB e a extensão ``delta``."""

    def __init__(self, config: DuckDBConfig, allowed_roots: Sequence[str]) -> None:
        """Abre a base em memória, carrega ``delta`` e trava a configuração.

        ``allowed_roots`` recebe URIs ``file://`` ou caminhos absolutos dos
        diretórios legíveis (por exemplo, a raiz Gold). Silver só entra por
        decisão explícita (§9.6).
        """
        if not allowed_roots:
            msg = "ao menos uma raiz permitida é obrigatória"
            raise ValueError(msg)
        self._config = config
        self._roots = tuple(_local_dir(r) for r in allowed_roots)
        Path(config.temp_directory).mkdir(parents=True, exist_ok=True)
        db_config: dict[str, str | bool | int | float | list[str]] = {
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
            "memory_limit": config.memory_limit,
            "threads": config.threads,
            "temp_directory": config.temp_directory,
            "max_temp_directory_size": config.max_temp_directory_size,
        }
        if config.extension_directory:
            db_config["extension_directory"] = config.extension_directory
        self._con = duckdb.connect(":memory:", config=db_config)
        self._con.execute("LOAD delta")
        roots_sql = ", ".join("'" + r.replace("'", "''") + "'" for r in self._roots)
        self._con.execute(f"SET allowed_directories = [{roots_sql}]")
        self._con.execute("SET enable_external_access = false")
        self._con.execute("SET lock_configuration = true")
        self._slots = threading.BoundedSemaphore(config.max_concurrent)
        self._closed = False

    # ------------------------------------------------------------- preparação

    def _scan_expr(self, table: PinnedTable) -> str:
        try:
            local = str(uri_to_local_path(table.table_uri))
        except StorageError as exc:
            raise QueryRejectedError(str(exc)) from exc
        if not any((local + "/").startswith(root) for root in self._roots):
            msg = f"tabela fora das raízes permitidas: {table.table_uri}"
            raise QueryRejectedError(msg)
        literal = "'" + table.table_uri.replace("'", "''") + "'"
        return f"delta_scan({literal}, version => {int(table.version)})"

    def render(self, query: ReadQuery) -> str:
        """Substitui ``{{alias}}`` e valida o SQL resultante."""
        used = set(_PLACEHOLDER.findall(query.sql_template))
        missing = used - set(query.tables)
        if missing:
            msg = f"aliases sem tabela vinculada: {sorted(missing)}"
            raise QueryRejectedError(msg)
        unused = set(query.tables) - used
        if unused:
            msg = f"tabelas vinculadas e não usadas: {sorted(unused)}"
            raise QueryRejectedError(msg)
        sql = _PLACEHOLDER.sub(
            lambda m: self._scan_expr(query.tables[m.group(1)]), query.sql_template
        )
        try:
            statements = duckdb.extract_statements(sql)
        except duckdb.Error as exc:
            msg = f"SQL inválido: {exc}"
            raise QueryRejectedError(msg) from exc
        if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
            kinds = [s.type.name for s in statements]
            msg = f"apenas uma instrução SELECT é permitida (recebido: {kinds})"
            raise QueryRejectedError(msg)
        return sql

    # ------------------------------------------------------------- execução

    def execute(self, query: ReadQuery) -> QueryResult:
        """Executa com limites de linhas, tempo e concorrência."""
        if self._closed:
            msg = "motor encerrado"
            raise QueryRejectedError(msg)
        sql = self.render(query)
        max_rows = min(query.max_rows or self._config.max_rows, self._config.max_rows)
        # sql já validado por render(); valores do usuário entram só como parâmetros.
        limited = f"SELECT * FROM ({sql}) AS odb_q LIMIT {max_rows + 1}"  # noqa: S608

        if not self._slots.acquire(timeout=self._config.busy_wait_s):
            msg = f"limite de {self._config.max_concurrent} consultas simultâneas atingido"
            raise QueryEngineBusyError(msg)
        cursor = self._con.cursor()
        timed_out = threading.Event()

        def _interrupt() -> None:
            timed_out.set()
            cursor.interrupt()

        timer = threading.Timer(self._config.timeout_s, _interrupt)
        started = time.perf_counter()
        try:
            timer.start()
            relation = cursor.execute(limited, dict(query.params))
            columns = [d[0] for d in relation.description or []]
            rows = relation.fetchall()
        except duckdb.InterruptException as exc:
            if timed_out.is_set():
                msg = f"consulta excedeu {self._config.timeout_s}s"
                raise QueryTimeoutError(msg) from exc
            raise  # pragma: no cover - interrupção externa
        except duckdb.PermissionException as exc:
            raise QueryRejectedError(str(exc)) from exc
        finally:
            timer.cancel()
            cursor.close()
            self._slots.release()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]
        logger.info(
            "query executed",
            extra={
                "tables": {a: f"{t.table_uri}@v{t.version}" for a, t in query.tables.items()},
                "param_names": sorted(query.params),
                "rows": len(rows),
                "truncated": truncated,
                "elapsed_ms": elapsed_ms,
            },
        )
        return QueryResult(
            columns=columns,
            rows=rows,
            truncated=truncated,
            elapsed_ms=elapsed_ms,
            tables=dict(query.tables),
        )

    def close(self) -> None:
        """Fecha a conexão DuckDB."""
        if not self._closed:
            self._con.close()
            self._closed = True

    def __enter__(self) -> DuckDBReadEngine:
        """Suporte a ``with``."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Fecha ao sair do bloco."""
        self.close()
