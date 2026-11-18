"""Smoke test do lakehouse (`odb smoke lakehouse`).

Exercita o caminho real de ponta a ponta na camada ``tmp``:

1. cria a tabela (v0), faz append (v1) e merge (v2) com lock PostgreSQL;
2. valida o perfil de protocolo após cada commit;
3. lê a v0 por Polars e por DuckDB (motor somente leitura) e compara;
4. confirma que a versão mais recente difere da v0, ou seja, que a leitura
   fixada é efetiva;
5. remove a tabela de smoke, salvo com ``--keep``.

A execução fica registrada em ``operations.pipeline_run``.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import polars as pl
from deltalake import DeltaTable

from odb_catalog import PostgresAdvisoryLock, make_engine, tracked_run
from odb_common.settings import Settings
from odb_common.storage import LakehouseLayout, Layer, uri_to_local_path
from odb_lakehouse import DeltaReader, DeltaWriter, validate_table
from odb_query_engine import DuckDBConfig, DuckDBReadEngine, PinnedTable, ReadQuery

SCHEMA: dict[str, pl.DataType] = {
    "obs_id": pl.Int64(),
    "territory_code": pl.String(),
    "reference_date": pl.Date(),
    "value": pl.Decimal(18, 4),
    "retrieved_at": pl.Datetime("us", "UTC"),
}


class SmokeError(RuntimeError):
    """Divergência detectada no smoke test."""


@dataclass(frozen=True, slots=True)
class SmokeReport:
    """Resumo do smoke test."""

    run_id: str
    table_uri: str
    versions: list[int]
    v0_rows: int
    latest_rows: int
    kept: bool


def _frame(ids: list[int], value: str) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "obs_id": ids,
            "territory_code": [f"{i:07d}" for i in ids],
            "reference_date": [date(2022, 7, 1)] * len(ids),
            "value": [Decimal(value)] * len(ids),
            "retrieved_at": [datetime.now(UTC)] * len(ids),
        },
        schema=SCHEMA,
    )


def run_lakehouse_smoke(settings: Settings, *, keep: bool = False) -> SmokeReport:
    """Executa o smoke test e lança ``SmokeError`` em qualquer divergência."""
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    engine = make_engine(settings, pool_size=2)
    try:
        with tracked_run(engine, "smoke.lakehouse", settings.code_version) as run_id:
            table_uri = layout.table_uri(Layer.TMP, "smoke", f"run_{run_id.replace('-', '_')}")
            writer = DeltaWriter(
                layout,
                PostgresAdvisoryLock(engine),
                disk_warn_percent=settings.disk_warn_percent,
                disk_block_percent=settings.disk_block_percent,
            )
            results = [
                writer.write(table_uri, _frame([1, 2, 3], "1.0000"), run_id=run_id),
                writer.write(table_uri, _frame([4], "1.0000"), run_id=run_id),
                writer.merge(table_uri, _frame([2, 5], "9.9999"), keys=["obs_id"], run_id=run_id),
            ]
            versions = [r.version for r in results]
            if versions != [0, 1, 2]:
                msg = f"versões inesperadas: {versions}"
                raise SmokeError(msg)

            reader = DeltaReader()
            v0_polars = reader.scan(table_uri, 0).sort("obs_id").collect()
            latest = reader.scan(table_uri, 2).sort("obs_id").collect()

            duck_config = DuckDBConfig.from_settings(settings)
            with DuckDBReadEngine(duck_config, [layout.layer_uri(Layer.TMP)]) as duck:
                result = duck.execute(
                    ReadQuery(
                        "SELECT obs_id, territory_code, value FROM {{t}} ORDER BY obs_id",
                        {"t": PinnedTable(table_uri, 0)},
                    )
                )
            polars_rows = v0_polars.select("obs_id", "territory_code", "value").rows()
            if list(result.rows) != polars_rows:
                msg = f"Polars e DuckDB divergem na v0: {polars_rows} != {list(result.rows)}"
                raise SmokeError(msg)
            if v0_polars.height != 3 or latest.height != 5:  # noqa: PLR2004
                msg = f"contagens inesperadas: v0={v0_polars.height}, v2={latest.height}"
                raise SmokeError(msg)
            validate_table(DeltaTable(table_uri))
            report = SmokeReport(
                run_id=run_id,
                table_uri=table_uri,
                versions=versions,
                v0_rows=v0_polars.height,
                latest_rows=latest.height,
                kept=keep,
            )
            if not keep:
                shutil.rmtree(Path(uri_to_local_path(table_uri)))
            return report
    finally:
        engine.dispose()
