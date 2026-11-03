"""Contratos de interoperabilidade Delta entre Polars, delta-rs e DuckDB.

Cada teste valida um recurso de que a arquitetura depende (§24.2 e §24.3).
Se algum falhar depois de uma atualização de dependências, a matriz de
compatibilidade (docs/development/compatibility-matrix.md) deixa de valer.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import polars as pl
import pytest
from deltalake import DeltaTable
from deltalake.exceptions import SchemaMismatchError

from tests.contracts.delta_interop.conftest import make_frame

pytestmark = pytest.mark.interop


def _duck_count(con: duckdb.DuckDBPyConnection, uri: str, version: int | None = None) -> int:
    if version is None:
        row = con.execute("SELECT count(*) FROM delta_scan(?)", [uri]).fetchone()
    else:
        row = con.execute(
            "SELECT count(*) FROM delta_scan(?, version => ?)", [uri, version]
        ).fetchone()
    assert row is not None
    return int(row[0])


def _assert_conservative_protocol(uri: str) -> None:
    protocol = DeltaTable(uri).protocol()
    assert protocol.min_reader_version == 1
    assert protocol.min_writer_version == 2
    assert not protocol.reader_features
    assert not protocol.writer_features


# ------------------------------------------------------------- protocolo e tipos


def test_polars_write_creates_conservative_protocol(table_path: str) -> None:
    make_frame([1, 2]).write_delta(table_path, mode="error")
    _assert_conservative_protocol(table_path)
    assert DeltaTable(table_path).version() == 0


def test_types_roundtrip_polars_and_duckdb(
    table_path: str, duck: duckdb.DuckDBPyConnection
) -> None:
    expected = make_frame([1, 2], value="1234.5678")
    expected.write_delta(table_path)

    polars_back = pl.scan_delta(table_path).sort("obs_id").collect()
    assert polars_back.schema == expected.schema
    assert polars_back.equals(expected)

    described = duck.execute("DESCRIBE SELECT * FROM delta_scan(?)", [table_path]).fetchall()
    types = {row[0]: row[1] for row in described}
    assert types == {
        "obs_id": "BIGINT",
        "territory_code": "VARCHAR",
        "uf": "VARCHAR",
        "reference_date": "DATE",
        "value": "DECIMAL(18,4)",
        "ratio": "DOUBLE",
        "is_estimate": "BOOLEAN",
        "retrieved_at": "TIMESTAMP WITH TIME ZONE",
    }
    row = duck.execute(
        "SELECT value, territory_code FROM delta_scan(?) WHERE obs_id = 1", [table_path]
    ).fetchone()
    assert row == (Decimal("1234.5678"), "3500001")


def test_utc_timestamp_is_stored_as_delta_timestamp(table_path: str) -> None:
    make_frame([1]).write_delta(table_path)
    fields = {f.name: f.type for f in DeltaTable(table_path).schema().fields}
    assert str(fields["retrieved_at"]) == 'PrimitiveType("timestamp")'


def test_naive_timestamp_escalates_protocol_guard(table_path: str) -> None:
    """Datetime sem fuso gera timestampNtz (reader 3, writer 7).

    O teste documenta o motivo pelo qual o validador do lakehouse rejeita
    datetimes sem fuso antes de qualquer escrita.
    """
    pl.DataFrame({"t": [datetime(2026, 1, 1)]}).write_delta(table_path)  # noqa: DTZ001
    protocol = DeltaTable(table_path).protocol()
    assert protocol.min_reader_version == 3
    assert "timestampNtz" in (protocol.reader_features or [])


# ------------------------------------------------------------- versões e time travel


def test_append_and_version_reads_agree(table_path: str, duck: duckdb.DuckDBPyConnection) -> None:
    make_frame([1, 2]).write_delta(table_path)  # v0
    make_frame([3]).write_delta(table_path, mode="append")  # v1
    make_frame([9], value="9.0000").write_delta(table_path, mode="overwrite")  # v2

    for version, rows in [(0, 2), (1, 3), (2, 1)]:
        assert pl.scan_delta(table_path, version=version).select(pl.len()).collect().item() == rows
        assert _duck_count(duck, table_path, version) == rows
    assert _duck_count(duck, table_path) == 1
    # overwrite preserva a versão anterior no histórico
    v1 = pl.scan_delta(table_path, version=1).sort("obs_id").collect()
    assert v1["obs_id"].to_list() == [1, 2, 3]


def test_nonexistent_version_is_an_error(table_path: str, duck: duckdb.DuckDBPyConnection) -> None:
    make_frame([1]).write_delta(table_path)
    with pytest.raises(Exception):  # noqa: B017, PT011 - tipo varia entre versões de delta-rs
        pl.scan_delta(table_path, version=5).collect()
    with pytest.raises(duckdb.IOException):
        _duck_count(duck, table_path, 5)


def test_file_uri_accepted_by_all_engines(table_path: str, duck: duckdb.DuckDBPyConnection) -> None:
    make_frame([1, 2]).write_delta(table_path)
    uri = Path(table_path).as_uri()
    assert uri.startswith("file:///")
    assert DeltaTable(uri).version() == 0
    assert pl.scan_delta(uri, version=0).select(pl.len()).collect().item() == 2
    assert _duck_count(duck, uri, 0) == 2


def test_checkpoint_then_time_travel(table_path: str, duck: duckdb.DuckDBPyConnection) -> None:
    make_frame([1]).write_delta(table_path)
    for i in range(2, 6):
        make_frame([i]).write_delta(table_path, mode="append")
    DeltaTable(table_path).create_checkpoint()
    make_frame([6]).write_delta(table_path, mode="append")  # v5, após checkpoint em v4

    log = sorted(p.name for p in (Path(table_path) / "_delta_log").iterdir())
    assert "00000000000000000004.checkpoint.parquet" in log
    assert _duck_count(duck, table_path) == 6
    assert _duck_count(duck, table_path, 2) == 3
    assert pl.scan_delta(table_path, version=0).select(pl.len()).collect().item() == 1


# ------------------------------------------------------------- merge e schema


def test_merge_upsert_keeps_protocol(table_path: str, duck: duckdb.DuckDBPyConnection) -> None:
    make_frame([1, 2]).write_delta(table_path)
    source = make_frame([2, 3], value="7.0000")
    metrics = (
        DeltaTable(table_path)
        .merge(
            source=source.to_arrow(),
            predicate="t.obs_id = s.obs_id",
            source_alias="s",
            target_alias="t",
        )
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute()
    )
    assert metrics["num_target_rows_updated"] == 1
    assert metrics["num_target_rows_inserted"] == 1
    _assert_conservative_protocol(table_path)
    rows = duck.execute(
        "SELECT obs_id, value FROM delta_scan(?) ORDER BY obs_id", [table_path]
    ).fetchall()
    assert rows == [(1, Decimal("1.0000")), (2, Decimal("7.0000")), (3, Decimal("7.0000"))]


def test_schema_evolution_requires_explicit_merge(
    table_path: str, duck: duckdb.DuckDBPyConnection
) -> None:
    make_frame([1]).write_delta(table_path)
    evolved = make_frame([2]).with_columns(pl.lit("nota").alias("note"))
    with pytest.raises(SchemaMismatchError):
        evolved.write_delta(table_path, mode="append")
    assert DeltaTable(table_path).version() == 0  # falha não cria versão

    evolved.write_delta(table_path, mode="append", delta_write_options={"schema_mode": "merge"})
    _assert_conservative_protocol(table_path)
    assert "note" not in pl.scan_delta(table_path, version=0).collect_schema()
    notes = duck.execute(
        "SELECT obs_id, note FROM delta_scan(?, version => 1) ORDER BY obs_id", [table_path]
    ).fetchall()
    assert notes == [(1, None), (2, "nota")]


# ------------------------------------------------------------- particionamento


def test_partitioned_table_filter_pushdown(
    table_path: str, duck: duckdb.DuckDBPyConnection
) -> None:
    pl.concat([make_frame([1, 2], uf="SP"), make_frame([3], uf="RJ")]).write_delta(
        table_path, delta_write_options={"partition_by": ["uf"]}
    )
    assert {p.name for p in Path(table_path).iterdir()} >= {"uf=SP", "uf=RJ"}
    assert duck.execute(
        "SELECT count(*) FROM delta_scan(?) WHERE uf = 'RJ'", [table_path]
    ).fetchone() == (1,)
    assert (
        pl.scan_delta(table_path).filter(pl.col("uf") == "SP").select(pl.len()).collect().item()
        == 2
    )
    _assert_conservative_protocol(table_path)


# ------------------------------------------------------------- riscos documentados


def test_duckdb_delta_extension_can_write_risk(
    table_path: str, duck: duckdb.DuckDBPyConnection
) -> None:
    """A extensão Delta do DuckDB consegue escrever via ATTACH.

    Por isso o adaptador de consulta nunca usa ATTACH, a Gold é montada como
    somente leitura nos serviços de consumo e o query_engine tem um teste
    próprio de bloqueio. Se este teste começar a falhar, o risco diminuiu, mas
    as proteções continuam necessárias.
    """
    make_frame([1]).write_delta(table_path)
    duck.execute(f"ATTACH '{table_path}' AS t (TYPE delta)")
    duck.execute("INSERT INTO t SELECT * FROM t")
    assert DeltaTable(table_path).version() == 1


# ------------------------------------------------------------- CSV (Bronze -> Silver)


def test_csv_read_polars_and_duckdb(tmp_path: Path, duck: duckdb.DuckDBPyConnection) -> None:
    """CSV no estilo de publicações oficiais: ';', vírgula decimal e códigos com zero à esquerda."""
    csv = tmp_path / "amostra.csv"
    csv.write_text(
        "cod;nome;valor\n0012;Município A;1234,5\n0034;Município B;-\n", encoding="utf-8"
    )

    frame = pl.scan_csv(
        csv,
        separator=";",
        schema={"cod": pl.String, "nome": pl.String, "valor": pl.String},
    ).collect()
    assert frame["cod"].to_list() == ["0012", "0034"]
    parsed = frame.select(pl.col("valor").str.replace(",", ".").cast(pl.Float64, strict=False))[
        "valor"
    ].to_list()
    assert parsed == [1234.5, None]  # '-' preservado como ausência, nunca como zero

    rows = duck.execute(
        "SELECT cod, valor FROM read_csv(?, delim=';', header=true, "
        "columns={'cod': 'VARCHAR', 'nome': 'VARCHAR', 'valor': 'VARCHAR'})",
        [str(csv)],
    ).fetchall()
    assert rows == [("0012", "1234,5"), ("0034", "-")]
