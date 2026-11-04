"""Bronze → Silver pela CLI, com PostgreSQL real e fontes simuladas a partir de fixtures reais."""

import json
from pathlib import Path

import polars as pl
import pytest
from deltalake import DeltaTable
from sqlalchemy import Engine, text
from typer.testing import CliRunner

from odb_cli import ingest as ingest_cli
from odb_cli.main import app
from odb_query_engine import DuckDBConfig, DuckDBReadEngine, PinnedTable, ReadQuery
from tests.ingestion_support import TEST_SOURCES, FakeSources
from tests.support import duckdb_extension_directory

pytestmark = pytest.mark.integration


@pytest.fixture
def lake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: Engine) -> Path:
    root = tmp_path / "lake"
    for layer in ("bronze", "silver", "gold", "tmp"):
        (root / layer).mkdir(parents=True)
    monkeypatch.setenv("ODB_LAKEHOUSE_ROOT_URI", root.as_uri())
    monkeypatch.setenv("ODB_SOURCES_CONFIG_DIR", str(TEST_SOURCES))
    monkeypatch.setenv("ODB_PG_DATABASE", "odb_test")
    monkeypatch.setattr(ingest_cli, "HTTP_TRANSPORT", FakeSources().transport())
    return root


def _q(engine: Engine, sql: str) -> list[tuple[object, ...]]:
    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql)).all()]


def _pairs(engine: Engine, sql: str) -> dict[str, str]:
    return {str(k): str(v) for k, v in _q(engine, sql)}


def test_silver_end_to_end(lake: Path, engine: Engine, tmp_path: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["ingest", "run", "--all"]).exit_code == 0
    built = runner.invoke(app, ["silver", "build", "--all"])
    assert built.exit_code == 0, built.output
    summary = json.loads(built.stdout)
    assert [(s["dataset_id"], s["status"]) for s in summary] == [
        ("ibge-dtb", "succeeded"),
        ("ibge-sidra-6579", "succeeded"),
        ("ibge-sidra-4714", "succeeded"),
        ("ibge-sidra-9605", "succeeded"),
        ("ibge-sidra-9718", "succeeded"),
        ("ibge-sidra-9578", "succeeded"),
        ("ibge-sidra-9971", "succeeded"),
        ("ibge-sidra-9970", "succeeded"),
    ]
    sidra_uri = summary[2]["target_uri"]
    version = summary[2]["delta_version"]
    assert sidra_uri.endswith("/silver/ibge/sidra_observation")

    # Linhagem: toda observação aponta para um artefato Bronze stored com o mesmo checksum.
    silver = (
        pl.read_delta(sidra_uri, version=version)
        .select("bronze_artifact_id", "bronze_checksum_sha256")
        .unique()
    )
    artifacts = _pairs(
        engine,
        "SELECT artifact_id::text, checksum_sha256 FROM operations.bronze_artifact "
        "WHERE ingestion_status = 'stored'",
    )
    assert all(artifacts[a] == c for a, c in silver.iter_rows())

    runs = _q(
        engine,
        "SELECT dataset_id, status, delta_version FROM operations.transformation_run "
        "ORDER BY started_at",
    )
    assert [r[1] for r in runs] == ["succeeded"] * 8
    checks = _pairs(
        engine,
        "SELECT c.check_id, c.status FROM quality.check_result c "
        "JOIN operations.transformation_run r USING (run_id) "
        "WHERE r.dataset_id = 'ibge-sidra-4714'",
    )
    assert checks["reconciliation.93.n3_n1"] == "pass"
    assert checks["reconciliation.6318.n3_n1"] == "pass"

    again = runner.invoke(app, ["silver", "build", "--all"])
    assert again.exit_code == 0
    assert {s["status"] for s in json.loads(again.stdout)} == {"skipped"}
    assert DeltaTable(sidra_uri).version() == summary[-1]["delta_version"]

    report = runner.invoke(app, ["quality", "report", "ibge-sidra-6579"])
    assert report.exit_code == 0
    assert "[PASS] reconciliation.9324.n3_n1" in report.stdout
    detailed = runner.invoke(app, ["quality", "report", "ibge-dtb", "--json"])
    assert json.loads(detailed.stdout)["run"]["contract"] == "dtb_municipality"
    assert runner.invoke(app, ["quality", "report", "nao-existe"]).exit_code == 1
    assert runner.invoke(app, ["silver", "build"]).exit_code == 2

    # A Silver é legível pelo motor de consulta (motor somente leitura, raiz Silver autorizada).
    config = DuckDBConfig(
        memory_limit="512MB",
        threads=2,
        temp_directory=str(tmp_path / "duck"),
        extension_directory=duckdb_extension_directory(),
    )
    with DuckDBReadEngine(config, [str(lake / "silver")]) as duck:
        result = duck.execute(
            ReadQuery(
                "SELECT value_status, count(*) FROM {{s}} GROUP BY 1 ORDER BY 1",
                {"s": PinnedTable(sidra_uri, version)},
            )
        )
    assert result.rows == [("valid", 825)]


def test_silver_failure_exit_code(lake: Path, engine: Engine) -> None:
    result = CliRunner().invoke(app, ["silver", "build", "ibge-sidra-4714"])  # sem ingestão
    assert result.exit_code == 1
    assert json.loads(result.stdout)[0]["status"] == "failed"
    assert _q(
        engine, "SELECT status FROM operations.pipeline_run WHERE command = 'silver.build'"
    ) == [("failed",)]
