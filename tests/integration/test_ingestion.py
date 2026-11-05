"""Ingestão de ponta a ponta com PostgreSQL real e fontes simuladas a partir de fixtures reais."""

import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import ProgrammingError
from typer.testing import CliRunner

from odb_catalog.ingestion import PostgresIngestionRegistry
from odb_cli import ingest as ingest_cli
from odb_cli.main import app
from odb_ingestion import load_sources
from tests.ingestion_support import TEST_SOURCES, FakeSources, fixture_bytes

pytestmark = pytest.mark.integration


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeSources:
    fake = FakeSources()
    monkeypatch.setattr(ingest_cli, "HTTP_TRANSPORT", fake.transport())
    return fake


@pytest.fixture
def lake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: Engine) -> Path:
    root = tmp_path / "lake"
    for layer in ("bronze", "silver", "gold", "tmp"):
        (root / layer).mkdir(parents=True)
    monkeypatch.setenv("ODB_LAKEHOUSE_ROOT_URI", root.as_uri())
    monkeypatch.setenv("ODB_SOURCES_CONFIG_DIR", str(TEST_SOURCES))
    monkeypatch.setenv("ODB_PG_DATABASE", "odb_test")
    return root


def _q(engine: Engine, sql: str, **params: object) -> list[tuple[object, ...]]:
    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql), params).all()]


def _counts(engine: Engine) -> dict[str, int]:
    rows = _q(
        engine, "SELECT ingestion_status, count(*) FROM operations.bronze_artifact GROUP BY 1"
    )
    return {str(k): int(str(v)) for k, v in rows}


def test_sync_catalog_is_idempotent(engine: Engine) -> None:
    registry = PostgresIngestionRegistry(engine)
    catalog = load_sources(TEST_SOURCES)
    registry.sync_catalog(catalog)
    first = _q(engine, "SELECT dataset_id, updated_at FROM catalog.dataset ORDER BY 1")
    registry.sync_catalog(catalog)
    assert _q(engine, "SELECT dataset_id, updated_at FROM catalog.dataset ORDER BY 1") == first
    assert [r[0] for r in first] == [
        "ibge-dtb",
        "ibge-malha-municipios-2022",
        "ibge-malha-uf-2022",
        "ibge-sidra-4714",
        "ibge-sidra-6579",
        "ibge-sidra-8176",
        "ibge-sidra-9578",
        "ibge-sidra-9605",
        "ibge-sidra-9606",
        "ibge-sidra-9718",
        "ibge-sidra-9723",
        "ibge-sidra-9765",
        "ibge-sidra-9954",
        "ibge-sidra-9970",
        "ibge-sidra-9971",
    ]
    assert _q(engine, "SELECT source_id, institution_id FROM catalog.source ORDER BY 1") == [
        ("ibge-geoftp", "ibge"),
        ("ibge-sidra", "ibge"),
    ]


def test_cli_ingest_run_rerun_and_status(lake: Path, fake: FakeSources, engine: Engine) -> None:
    runner = CliRunner()
    first = runner.invoke(app, ["ingest", "run", "--all"])
    assert first.exit_code == 0, first.output
    reports = json.loads(first.stdout)
    assert [(r["dataset_id"], r["status"]) for r in reports] == [
        ("ibge-sidra-6579", "succeeded"),
        ("ibge-sidra-4714", "succeeded"),
        ("ibge-sidra-9605", "succeeded"),
        ("ibge-sidra-9718", "succeeded"),
        ("ibge-sidra-9578", "succeeded"),
        ("ibge-sidra-9971", "succeeded"),
        ("ibge-sidra-9970", "succeeded"),
        ("ibge-sidra-9723", "succeeded"),
        ("ibge-sidra-9954", "succeeded"),
        ("ibge-sidra-9606", "succeeded"),
        ("ibge-sidra-8176", "succeeded"),
        ("ibge-sidra-9765", "succeeded"),
        ("ibge-dtb", "succeeded"),
        ("ibge-malha-uf-2022", "succeeded"),
        ("ibge-malha-municipios-2022", "succeeded"),
    ]
    files = sorted(p for p in (lake / "bronze").rglob("*") if p.is_file())
    # 6579: 22 anos; 4714: 1; 9605: 2 censos; 9718: 3 variáveis x 3 localizações;
    # 9578: 3 variáveis; 9971 e 9970: 1 cada (teste só no nível Brasil, sem divisão); 9723: 1;
    # 9954: 2 variáveis; 9606: 2 censos; 8176 e 9765: 1 cada; DTB e 2 malhas: 1 cada.
    assert len(files) == 22 + 1 + 2 + 9 + 3 + 1 + 1 + 1 + 2 + 2 + 1 + 1 + 1 + 2

    assert _counts(engine) == {"stored": 49}
    meta = _q(
        engine,
        "SELECT source_url, checksum_sha256, file_size_bytes, http_status, license_id, "
        "access_classification, storage_uri, reference_period, content_type "
        "FROM operations.bronze_artifact WHERE partition_key = 'n1n2n3-p2025'",
    )[0]
    assert (
        meta[0] == "https://apisidra.ibge.gov.br/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2025"
    )
    assert len(str(meta[1])) == 64
    assert meta[3] == 200
    assert meta[4:6] == ("ibge-reuso-com-citacao", "public_conditional")
    assert Path(str(meta[6]).removeprefix("file://")).is_file()
    assert meta[7] == "2025"

    second = runner.invoke(app, ["ingest", "run", "--all"])
    assert second.exit_code == 0, second.output
    assert sorted(p for p in (lake / "bronze").rglob("*") if p.is_file()) == files
    assert _counts(engine) == {"stored": 49, "reused": 26, "not_modified": 1}
    runs = _q(engine, "SELECT status FROM operations.pipeline_run WHERE command = 'ingest.run'")
    assert runs == [("succeeded",), ("succeeded",)]

    status = runner.invoke(app, ["ingest", "status", "--limit", "30"])
    assert status.exit_code == 0
    assert "ibge-sidra-6579" in status.stdout
    assert "reused=2" in status.stdout


def test_cli_failure_exit_code_and_isolation(lake: Path, fake: FakeSources, engine: Engine) -> None:
    fake.overrides["/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2026"] = lambda _r: httpx.Response(
        200, content=fixture_bytes("t6579_n3_p1900_empty.json")
    )
    result = CliRunner().invoke(app, ["ingest", "run", "ibge-sidra-6579", "ibge-dtb"])
    assert result.exit_code == 1
    statuses = {r["dataset_id"]: r["status"] for r in json.loads(result.stdout)}
    assert statuses == {"ibge-sidra-6579": "failed", "ibge-dtb": "succeeded"}
    assert _q(engine, "SELECT status FROM operations.pipeline_run") == [("failed",)]
    assert _q(
        engine, "SELECT count(*) FROM operations.watermark WHERE dataset_id = 'ibge-sidra-6579'"
    ) == [(0,)]
    quarantined = _q(
        engine,
        "SELECT storage_uri FROM operations.bronze_artifact WHERE ingestion_status = 'quarantined'",
    )
    assert "/quarantine/" in str(quarantined[0][0])


def test_cli_plan_sources_and_usage_errors(lake: Path, fake: FakeSources) -> None:
    runner = CliRunner()
    plan = runner.invoke(app, ["ingest", "plan", "ibge-sidra-4714"])
    assert plan.exit_code == 0, plan.output
    assert json.loads(plan.stdout)["requests"][0]["reference_period"] == "2022"
    assert runner.invoke(app, ["ingest", "run"]).exit_code == 2
    unknown = runner.invoke(app, ["ingest", "run", "nao-existe"])
    assert unknown.exit_code != 0
    listed = runner.invoke(app, ["sources", "list"])
    assert "ibge-sidra-6579" in listed.stdout
    health = runner.invoke(app, ["sources", "health"])
    assert health.exit_code == 0, health.output
    fake.overrides["/values/t/6579/n1/all/v/9324/p/last"] = lambda _r: httpx.Response(503)
    assert runner.invoke(app, ["sources", "health"]).exit_code == 1


def test_roles_on_ingestion_tables(
    engine: Engine, pipeline_engine: Engine, reader_engine: Engine
) -> None:
    pipeline = PostgresIngestionRegistry(pipeline_engine)
    pipeline.sync_catalog(load_sources(TEST_SOURCES))
    pipeline.start_ingestion("00000000-0000-0000-0000-000000000001", "ibge-dtb", None, {})
    pipeline.finish_ingestion("00000000-0000-0000-0000-000000000001", "succeeded", {}, None)
    with reader_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM catalog.dataset")).scalar() == 15
    with (
        pytest.raises(ProgrammingError, match="permission denied"),
        reader_engine.connect() as conn,
    ):
        conn.execute(text("SELECT * FROM operations.bronze_artifact"))
