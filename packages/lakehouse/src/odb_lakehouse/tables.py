"""Escrita e leitura de tabelas Delta (caminho oficial: Polars + delta-rs).

Regras impostas aqui:

* toda escrita passa pela validação de schema e protocolo, pelo lock de escrita
  da tabela e pela checagem de disco;
* cada commit registra ``odb.run_id`` e ``odb.operation`` no ``commitInfo``,
  para linhagem;
* a leitura exige versão explícita. Não há "leia a mais recente" implícito no
  caminho de consumo, e a versão vem do manifesto de publicação.

Escritas recebem ``pl.DataFrame`` materializado. Para volumes acima da memória,
a evolução prevista é ``LazyFrame.sink_delta`` ou escrita em lotes, a avaliar
na Fase 3 com benchmarks.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import polars as pl
from deltalake import CommitProperties, DeltaTable

from odb_common.storage import LakehouseLayout, Layer, StorageError, uri_to_local_path
from odb_lakehouse.disk import ensure_capacity
from odb_lakehouse.locking import TableWriteLock
from odb_lakehouse.protocol import validate_schema, validate_table

WriteMode = Literal["error", "append", "overwrite"]
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_WRITABLE_LAYERS = frozenset({Layer.SILVER, Layer.GOLD, Layer.TMP})


class TableWriteError(RuntimeError):
    """Escrita rejeitada por regra da plataforma."""


@dataclass(frozen=True, slots=True)
class WriteResult:
    """Resultado de um commit Delta."""

    table_uri: str
    version: int
    operation: str
    run_id: str
    metrics: dict[str, Any]


def _commit_properties(run_id: str, operation: str) -> CommitProperties:
    return CommitProperties(custom_metadata={"odb.run_id": run_id, "odb.operation": operation})


def _check_identifiers(names: Sequence[str], what: str) -> None:
    bad = [n for n in names if not _IDENTIFIER.fullmatch(n)]
    if bad:
        msg = f"{what} com nome inválido (use snake_case minúsculo): {bad}"
        raise TableWriteError(msg)


class DeltaWriter:
    """Escritor único das camadas Silver, Gold e temporária."""

    def __init__(
        self,
        layout: LakehouseLayout,
        lock: TableWriteLock,
        *,
        disk_warn_percent: int = 80,
        disk_block_percent: int = 90,
    ) -> None:
        """Associa o escritor a um lakehouse e a uma implementação de lock."""
        self._layout = layout
        self._lock = lock
        self._disk_warn = disk_warn_percent
        self._disk_block = disk_block_percent

    def _preflight(self, table_uri: str, frame: pl.DataFrame) -> None:
        try:
            layer = self._layout.layer_of(table_uri)
        except StorageError as exc:
            raise TableWriteError(str(exc)) from exc
        if layer not in _WRITABLE_LAYERS:
            msg = f"camada {layer.value} não aceita tabelas Delta: {table_uri}"
            raise TableWriteError(msg)
        _check_identifiers(frame.columns, "colunas")
        validate_schema(frame.schema)
        ensure_capacity(
            uri_to_local_path(self._layout.layer_uri(layer)), self._disk_warn, self._disk_block
        )

    def _committed(self, table_uri: str, operation: str, run_id: str) -> WriteResult:
        table = DeltaTable(table_uri)
        validate_table(table)
        last = table.history(1)[0]
        if last.get("odb.run_id") != run_id:  # pragma: no cover - violação do lock
            msg = f"último commit de {table_uri} não pertence à execução {run_id}"
            raise TableWriteError(msg)
        return WriteResult(
            table_uri=table_uri,
            version=table.version(),
            operation=operation,
            run_id=run_id,
            metrics=dict(last.get("operationMetrics", {})),
        )

    def write(
        self,
        table_uri: str,
        frame: pl.DataFrame,
        *,
        run_id: str,
        mode: WriteMode = "append",
        partition_by: Sequence[str] | None = None,
        evolve_schema: bool = False,
        replace_where: Mapping[str, str] | None = None,
    ) -> WriteResult:
        """Grava ``frame`` com o modo indicado e devolve a nova versão.

        ``evolve_schema=True`` permite apenas acrescentar colunas (``schema_mode
        = merge``). Remoção ou troca de tipo continua bloqueada pelo delta-rs.

        ``replace_where`` (exige ``mode="overwrite"``) substitui apenas as linhas
        que satisfazem as igualdades informadas, por exemplo
        ``{"table_id": "6579"}``. Linhas que deixaram de existir na fonte são
        removidas, o que um merge não faz. Todas as linhas de ``frame`` precisam
        satisfazer o predicado.
        """
        self._preflight(table_uri, frame)
        predicate = None
        if replace_where is not None:
            predicate = self._replace_predicate(frame, replace_where, mode)
        with self._lock.hold(table_uri):
            exists = DeltaTable.is_deltatable(table_uri)
            if exists:
                current = DeltaTable(table_uri)
                validate_table(current)
                current_parts = list(current.metadata().partition_columns)
                if partition_by is not None and list(partition_by) != current_parts:
                    msg = (
                        f"particionamento {list(partition_by)} difere do existente "
                        f"{current_parts} em {table_uri}"
                    )
                    raise TableWriteError(msg)
            elif mode == "append":
                mode = "error"  # primeira escrita cria a tabela
            options: dict[str, Any] = {
                "commit_properties": _commit_properties(run_id, f"write:{mode}")
            }
            if partition_by and not exists:
                _check_identifiers(partition_by, "colunas de partição")
                options["partition_by"] = list(partition_by)
            if evolve_schema:
                options["schema_mode"] = "merge"
            operation = f"write:{mode}"
            if predicate is not None and exists:
                options["predicate"] = predicate
                operation = "write:replace_where"
                options["commit_properties"] = _commit_properties(run_id, operation)
            elif predicate is not None:
                mode = "error"  # primeira escrita cria a tabela
            frame.write_delta(table_uri, mode=mode, delta_write_options=options)
            return self._committed(table_uri, operation, run_id)

    @staticmethod
    def _replace_predicate(
        frame: pl.DataFrame, replace_where: Mapping[str, str], mode: WriteMode
    ) -> str:
        if mode != "overwrite":
            msg = "replace_where exige mode='overwrite'"
            raise TableWriteError(msg)
        if not replace_where:
            msg = "replace_where exige ao menos uma coluna"
            raise TableWriteError(msg)
        _check_identifiers(list(replace_where), "colunas de replace_where")
        for column, value in replace_where.items():
            if column not in frame.columns:
                msg = f"coluna de replace_where ausente no lote: {column}"
                raise TableWriteError(msg)
            outside = frame.filter(pl.col(column).cast(pl.String) != value).height
            if outside:
                msg = f"{outside} linhas do lote não satisfazem {column} = {value!r}"
                raise TableWriteError(msg)
        return " AND ".join(
            f"{col} = '{str(val).replace(chr(39), chr(39) * 2)}'"
            for col, val in replace_where.items()
        )

    def merge(
        self,
        table_uri: str,
        frame: pl.DataFrame,
        *,
        keys: Sequence[str],
        run_id: str,
    ) -> WriteResult:
        """Upsert por chave de negócio em tabela existente.

        Exige chaves não nulas e únicas no lote de origem. Linhas da tabela que
        não aparecem no lote permanecem inalteradas. Não há exclusão por merge.
        """
        self._preflight(table_uri, frame)
        if not keys:
            msg = "merge exige ao menos uma coluna de chave"
            raise TableWriteError(msg)
        _check_identifiers(keys, "chaves")
        missing = [k for k in keys if k not in frame.columns]
        if missing:
            msg = f"chaves ausentes no lote: {missing}"
            raise TableWriteError(msg)
        key_frame = frame.select(keys)
        if key_frame.null_count().sum_horizontal().item() > 0:
            msg = "chaves de merge contêm nulos"
            raise TableWriteError(msg)
        if key_frame.is_duplicated().any():
            msg = f"chaves de merge duplicadas no lote: {list(keys)}"
            raise TableWriteError(msg)

        with self._lock.hold(table_uri):
            if not DeltaTable.is_deltatable(table_uri):
                msg = f"merge exige tabela existente: {table_uri}"
                raise TableWriteError(msg)
            table = DeltaTable(table_uri)
            validate_table(table)
            target_columns = [f.name for f in table.schema().fields]
            if sorted(target_columns) != sorted(frame.columns):
                msg = f"colunas do lote {frame.columns} diferem da tabela {target_columns}"
                raise TableWriteError(msg)
            predicate = " AND ".join(f't."{k}" = s."{k}"' for k in keys)
            (
                table.merge(
                    source=frame.to_arrow(),
                    predicate=predicate,
                    source_alias="s",
                    target_alias="t",
                    commit_properties=_commit_properties(run_id, "merge"),
                )
                .when_matched_update_all()
                .when_not_matched_insert_all()
                .execute()
            )
            return self._committed(table_uri, "merge", run_id)


class DeltaReader:
    """Leitura de tabelas Delta em versões explícitas."""

    def current_version(self, table_uri: str) -> int:
        """Versão mais recente registrada no log (uso interno de engenharia)."""
        return DeltaTable(table_uri).version()

    def has_version(self, table_uri: str, version: int) -> bool:
        """Indica se a versão pode ser carregada, isto é, se ainda não foi removida por limpeza."""
        if version < 0 or not DeltaTable.is_deltatable(table_uri):
            return False
        try:
            DeltaTable(table_uri, version=version)
        except Exception:
            return False
        return True

    def scan(self, table_uri: str, version: int) -> pl.LazyFrame:
        """``LazyFrame`` de uma versão fixada."""
        if version < 0:
            msg = f"versão inválida: {version}"
            raise ValueError(msg)
        return pl.scan_delta(table_uri, version=version)

    def history(self, table_uri: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Histórico de commits, do mais recente para o mais antigo."""
        return list(DeltaTable(table_uri).history(limit))
