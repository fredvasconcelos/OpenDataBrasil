import os
import stat
import threading
from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest

from odb_common.settings import Settings
from odb_common.storage import LakehouseLayout, Layer
from odb_query_engine import (
    DuckDBConfig,
    DuckDBReadEngine,
    PinnedTable,
    QueryEngineBusyError,
    QueryRejectedError,
    QueryTimeoutError,
    ReadQuery,
)
from tests.contracts.delta_interop.conftest import make_frame
from tests.support import duckdb_extension_directory


@pytest.fixture
def layout(tmp_path: Path) -> LakehouseLayout:
    return LakehouseLayout(tmp_path.as_uri())


@pytest.fixture
def gold_uri(layout: LakehouseLayout) -> str:
    uri = layout.table_uri(Layer.GOLD, "demo", "fact_obs")
    make_frame([1, 2]).write_delta(uri)  # v0: 2 linhas
    make_frame([3]).write_delta(uri, mode="append")  # v1: 3 linhas
    return uri


@pytest.fixture
def silver_uri(layout: LakehouseLayout) -> str:
    uri = layout.table_uri(Layer.SILVER, "demo", "obs")
    make_frame([1]).write_delta(uri)
    return uri


def _config(tmp_path: Path, **kw: object) -> DuckDBConfig:
    base: dict[str, object] = {
        "memory_limit": "512MB",
        "threads": 2,
        "temp_directory": str(tmp_path / "tmp" / "duckdb"),
        "max_temp_directory_size": "1GB",
        "extension_directory": duckdb_extension_directory(),
    }
    base.update(kw)
    return DuckDBConfig(**base)  # type: ignore[arg-type]


@pytest.fixture
def engine(tmp_path: Path, layout: LakehouseLayout) -> Iterator[DuckDBReadEngine]:
    with DuckDBReadEngine(_config(tmp_path), [layout.layer_uri(Layer.GOLD)]) as eng:
        yield eng


def _count(uri: str, version: int) -> ReadQuery:
    return ReadQuery("SELECT count(*) AS n FROM {{ fact }}", {"fact": PinnedTable(uri, version)})


def test_reads_pinned_versions(engine: DuckDBReadEngine, gold_uri: str) -> None:
    assert engine.execute(_count(gold_uri, 0)).rows == [(2,)]
    result = engine.execute(_count(gold_uri, 1))
    assert result.rows == [(3,)]
    assert result.columns == ["n"]
    assert result.tables["fact"].version == 1
    assert not result.truncated


def test_named_parameters(engine: DuckDBReadEngine, gold_uri: str) -> None:
    query = ReadQuery(
        "SELECT obs_id FROM {{fact}} WHERE obs_id >= $min_id ORDER BY obs_id",
        {"fact": PinnedTable(gold_uri, 1)},
        params={"min_id": 2},
    )
    assert engine.execute(query).rows == [(2,), (3,)]


def test_row_limit_and_truncation(tmp_path: Path, layout: LakehouseLayout, gold_uri: str) -> None:
    with DuckDBReadEngine(_config(tmp_path, max_rows=2), [layout.layer_uri(Layer.GOLD)]) as eng:
        query = ReadQuery(
            "SELECT obs_id FROM {{f}} ORDER BY obs_id", {"f": PinnedTable(gold_uri, 1)}
        )
        result = eng.execute(query)
        assert result.rows == [(1,), (2,)]
        assert result.truncated
        bigger = ReadQuery(query.sql_template, query.tables, max_rows=50)
        assert len(eng.execute(bigger).rows) == 2  # max_rows da consulta não excede o do motor
        smaller = ReadQuery(query.sql_template, query.tables, max_rows=1)
        assert eng.execute(smaller).rows == [(1,)]


@pytest.mark.parametrize(
    "template",
    [
        "INSERT INTO x SELECT * FROM {{f}}",
        "SELECT * FROM {{f}}; DROP TABLE x",
        "COPY (SELECT * FROM {{f}}) TO '/tmp/out.csv'",
        "ATTACH '/tmp/x' AS w (TYPE delta)",
        "SET enable_external_access = true",
        "EXPLAIN SELECT * FROM {{f}}",
        "SELEC broken FROM {{f}}",
    ],
)
def test_non_select_statements_rejected(
    engine: DuckDBReadEngine, gold_uri: str, template: str
) -> None:
    tables = {"f": PinnedTable(gold_uri, 0)} if "{{f}}" in template else {}
    with pytest.raises(QueryRejectedError):
        engine.execute(ReadQuery(template, tables))


def test_binding_rules(engine: DuckDBReadEngine, gold_uri: str) -> None:
    with pytest.raises(QueryRejectedError, match="sem tabela"):
        engine.execute(ReadQuery("SELECT * FROM {{missing}}", {}))
    with pytest.raises(QueryRejectedError, match="não usadas"):
        engine.execute(ReadQuery("SELECT 1", {"f": PinnedTable(gold_uri, 0)}))
    with pytest.raises(QueryRejectedError, match="aliases inválidos"):
        ReadQuery("SELECT 1", {"Bad-Alias": PinnedTable(gold_uri, 0)})
    with pytest.raises(QueryRejectedError, match="versão inválida"):
        PinnedTable(gold_uri, -1)


def test_tables_outside_allowed_roots_rejected(engine: DuckDBReadEngine, silver_uri: str) -> None:
    with pytest.raises(QueryRejectedError, match="fora das raízes"):
        engine.execute(_count(silver_uri, 0))
    with pytest.raises(QueryRejectedError, match="file://"):
        engine.execute(_count("s3://bucket/gold/t", 0))


def test_sandbox_blocks_direct_file_access(engine: DuckDBReadEngine, silver_uri: str) -> None:
    """Mesmo um template mal escrito não consegue ler fora da Gold."""
    silver_path = silver_uri.removeprefix("file://")
    with pytest.raises(QueryRejectedError, match=r"(?i)permission"):
        engine.execute(ReadQuery(f"SELECT count(*) FROM delta_scan('{silver_path}')", {}))
    with pytest.raises(QueryRejectedError, match=r"(?i)permission"):
        engine.execute(ReadQuery("SELECT * FROM read_csv('/etc/passwd')", {}))


def test_timeout_interrupts_and_engine_recovers(
    tmp_path: Path, layout: LakehouseLayout, gold_uri: str
) -> None:
    cfg = _config(tmp_path, timeout_s=0.2)
    with DuckDBReadEngine(cfg, [layout.layer_uri(Layer.GOLD)]) as eng:
        slow = ReadQuery(
            "SELECT count(*) FROM range(100000000000) a, {{f}} b", {"f": PinnedTable(gold_uri, 0)}
        )
        with pytest.raises(QueryTimeoutError):
            eng.execute(slow)
        assert eng.execute(_count(gold_uri, 0)).rows == [(2,)]


def test_concurrency_limit(tmp_path: Path, layout: LakehouseLayout, gold_uri: str) -> None:
    cfg = _config(tmp_path, max_concurrent=1, busy_wait_s=0.05)
    with DuckDBReadEngine(cfg, [layout.layer_uri(Layer.GOLD)]) as eng:
        eng._slots.acquire()  # simula uma consulta em andamento
        try:
            with pytest.raises(QueryEngineBusyError):
                eng.execute(_count(gold_uri, 0))
        finally:
            eng._slots.release()
        assert eng.execute(_count(gold_uri, 0)).rows == [(2,)]


def test_parallel_queries_are_consistent(engine: DuckDBReadEngine, gold_uri: str) -> None:
    results: list[object] = []
    errors: list[BaseException] = []

    def worker(version: int) -> None:
        try:
            results.append((version, engine.execute(_count(gold_uri, version)).rows[0][0]))
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i % 2,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert sorted(set(results)) == [(0, 2), (1, 3)]  # type: ignore[type-var]


def test_closed_engine_and_config_validation(tmp_path: Path, gold_uri: str) -> None:
    with pytest.raises(ValueError, match="raiz"):
        DuckDBReadEngine(_config(tmp_path), [])
    eng = DuckDBReadEngine(_config(tmp_path), [str(tmp_path / "gold")])
    eng.close()
    eng.close()
    with pytest.raises(QueryRejectedError, match="encerrado"):
        eng.execute(_count(gold_uri, 0))


def test_config_from_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ODB_CONFIG_DIR", str(tmp_path))
    settings = Settings(duckdb_threads=3, duckdb_extension_directory="/opt/ext")
    cfg = DuckDBConfig.from_settings(settings)
    assert cfg.threads == 3
    assert cfg.extension_directory == "/opt/ext"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões de arquivo")
def test_read_only_mount_blocks_writes_but_allows_reads(
    tmp_path: Path, layout: LakehouseLayout, gold_uri: str
) -> None:
    """Simula a montagem ':ro' da Gold no serviço de consumo."""
    gold_root = Path(layout.layer_uri(Layer.GOLD).removeprefix("file://"))
    paths = [gold_root, *gold_root.rglob("*")]
    for p in paths:
        p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    try:
        with pytest.raises(Exception):  # noqa: B017, PT011 - erro de I/O do delta-rs
            make_frame([9]).write_delta(gold_uri, mode="append")
        with DuckDBReadEngine(_config(tmp_path), [str(gold_root)]) as eng:
            assert eng.execute(_count(gold_uri, 1)).rows == [(3,)]
    finally:
        for p in paths:
            p.chmod(p.stat().st_mode | stat.S_IWUSR)
    assert pl.scan_delta(gold_uri).select(pl.len()).collect().item() == 3
