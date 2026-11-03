import json
from pathlib import Path

import httpx
import polars as pl
import pytest
from deltalake import DeltaTable

from odb_common.storage import LakehouseLayout
from odb_ingestion import BronzeStore, HttpClient, IngestionRunner, build_connectors, load_sources
from odb_ingestion.contract import BaseConnector
from odb_lakehouse import DeltaReader, DeltaWriter, InProcessLock
from odb_processing.silver import SilverBuilder
from tests.ingestion_support import TEST_SOURCES, FakeSources, InMemoryRegistry, fixture_bytes
from tests.silver_support import InMemorySilverRegistry


class Env:
    def __init__(self, tmp_path: Path) -> None:
        self.catalog = load_sources(TEST_SOURCES)
        self.layout = LakehouseLayout((tmp_path / "lake").as_uri())
        self.fake = FakeSources()
        self.ingestion = InMemoryRegistry()

        def factory(connector: BaseConnector) -> HttpClient:
            return HttpClient(
                connector.source.http, transport=self.fake.transport(), sleep=lambda _s: None
            )

        self.runner = IngestionRunner(
            self.catalog,
            build_connectors(self.catalog),
            BronzeStore(self.layout),
            self.ingestion,
            factory,
        )
        self.registry = InMemorySilverRegistry(self.ingestion)
        self.builder = SilverBuilder(
            self.catalog,
            self.layout,
            DeltaWriter(self.layout, InProcessLock()),
            self.registry,
            code_version="test",
        )

    def ingest(self, *datasets: str) -> None:
        for d in datasets:
            assert self.runner.run(d).status == "succeeded"


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


ALL = ["ibge-sidra-6579", "ibge-sidra-4714", "ibge-dtb"]


def test_build_all_with_lineage_and_reference(env: Env) -> None:
    env.ingest(*ALL)
    runs = env.builder.build_many(ALL)
    assert [r.dataset_id for r in runs] == ["ibge-dtb", "ibge-sidra-6579", "ibge-sidra-4714"]
    assert [r.status for r in runs] == ["succeeded"] * 3, [r.error for r in runs]
    dtb, s6579, s4714 = runs
    assert dtb.rows == 5571
    assert s6579.rows == 22 * 33
    assert s4714.rows == 99
    assert s6579.target_uri == s4714.target_uri  # tabela genérica sidra_observation

    reader = DeltaReader()
    silver = reader.scan(s4714.target_uri, s4714.delta_version).collect()  # type: ignore[arg-type]
    assert dict(silver.group_by("table_id").len().iter_rows()) == {"6579": 726, "4714": 99}
    stored = {a.artifact_id: a for a in env.ingestion.by_status("stored")}
    assert set(silver["bronze_artifact_id"].unique().to_list()) <= set(stored)
    one = silver.filter(pl.col("table_id") == "6579").row(0, named=True)
    assert stored[one["bronze_artifact_id"]].checksum_sha256 == one["bronze_checksum_sha256"]
    assert DeltaTable(s4714.target_uri).protocol().min_writer_version == 2

    checks = {c.check_id: c.status.value for c in env.registry.checks[s6579.run_id]}
    assert checks["reconciliation.9324.n3_n1"] == "pass"
    assert checks["reference.municipality"] == "pass"  # sem nível 6 nos testes
    dtb_frame = reader.scan(dtb.target_uri, dtb.delta_version).collect()  # type: ignore[arg-type]
    assert dtb_frame["reference_year"].unique().to_list() == ["2025"]


def test_rebuild_without_changes_is_skipped(env: Env) -> None:
    env.ingest("ibge-sidra-4714")
    first = env.builder.build("ibge-sidra-4714")
    second = env.builder.build("ibge-sidra-4714")
    assert second.status == "skipped"
    assert second.delta_version == first.delta_version
    assert DeltaTable(first.target_uri).version() == first.delta_version
    forced = env.builder.build("ibge-sidra-4714", force=True)
    assert forced.status == "succeeded"
    assert forced.delta_version == first.delta_version + 1


def test_revision_replaces_only_that_table(env: Env) -> None:
    env.ingest("ibge-sidra-6579", "ibge-sidra-4714")
    env.builder.build("ibge-sidra-6579")
    census = env.builder.build("ibge-sidra-4714")
    payload = json.loads(fixture_bytes("t6579_n1n2n3_p2025.json"))
    payload[1]["V"] = str(int(payload[1]["V"]) + 1)  # revisão do total Brasil 2025
    env.fake.overrides["/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2025"] = lambda _r: (
        httpx.Response(200, content=json.dumps(payload).encode())
    )
    env.ingest("ibge-sidra-6579")
    revised = env.builder.build("ibge-sidra-6579")
    assert revised.status == "succeeded"
    assert revised.delta_version == census.delta_version + 1  # type: ignore[operator]
    frame = DeltaReader().scan(revised.target_uri, revised.delta_version).collect()
    assert dict(frame.group_by("table_id").len().iter_rows()) == {"6579": 726, "4714": 99}
    brasil = frame.filter(
        (pl.col("table_id") == "6579")
        & (pl.col("period") == "2025")
        & (pl.col("territorial_level") == "1")
    )
    assert brasil["value_raw"].to_list() == [payload[1]["V"]]
    checks = {c.check_id: c.status.value for c in env.registry.checks[revised.run_id]}
    assert (
        checks["reconciliation.9324.n3_n1"] == "warn"
    )  # revisão quebrou a soma: aviso, não bloqueio


def test_failed_ingestion_keeps_last_valid_silver(env: Env) -> None:
    env.ingest("ibge-sidra-6579", "ibge-sidra-4714")
    env.builder.build("ibge-sidra-6579")
    env.builder.build("ibge-sidra-4714")
    payload = json.loads(fixture_bytes("t6579_n1n2n3_p2025.json"))
    payload = payload[:-1]  # IBGE remove uma linha na revisão
    env.fake.overrides["/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2025"] = lambda _r: (
        httpx.Response(200, content=json.dumps(payload).encode())
    )
    # A validação da ingestão (exatamente 33 linhas) rejeita a resposta truncada.
    assert env.runner.run("ibge-sidra-6579").status == "failed"
    rebuilt = env.builder.build("ibge-sidra-6579")
    assert (
        rebuilt.status == "skipped"
    )  # watermark não avançou: a Silver continua na última versão válida


def test_failures_are_recorded(env: Env, tmp_path: Path) -> None:
    missing = env.builder.build("ibge-sidra-4714")
    assert missing.status == "failed"
    assert "nenhum artefato" in (missing.error or "")

    env.ingest("ibge-sidra-4714")
    stored = env.ingestion.by_status("stored")[0]
    path = Path(str(stored.storage_uri).removeprefix("file://"))
    path.chmod(0o644)
    path.write_bytes(b"[]")
    corrupted = env.builder.build("ibge-sidra-4714")
    assert corrupted.status == "failed"
    assert "corrompido" in (corrupted.error or "")


def test_blocking_quality_prevents_write(env: Env) -> None:
    payload = json.loads(fixture_bytes("t4714_n1n2n3_p2022.json"))
    payload[1]["V"] = "1,5"  # valor não reconhecido
    env.fake.overrides["/values/t/4714/n1/all/n2/all/n3/all/v/93,6318,614/p/2022"] = lambda _r: (
        httpx.Response(200, content=json.dumps(payload).encode())
    )
    env.ingest("ibge-sidra-4714")
    run = env.builder.build("ibge-sidra-4714")
    assert run.status == "failed"
    assert "values.conversion_error" in (run.error or "")
    assert not DeltaTable.is_deltatable(run.target_uri)
    assert any(c.status.value == "fail" for c in env.registry.checks[run.run_id])


def test_incompatible_schema_blocks(env: Env) -> None:
    env.ingest("ibge-sidra-4714")
    first = env.builder.build("ibge-sidra-4714")
    current = pl.read_delta(first.target_uri)
    current.with_columns(pl.lit("x").alias("legacy")).write_delta(
        first.target_uri, mode="overwrite", delta_write_options={"schema_mode": "overwrite"}
    )
    run = env.builder.build("ibge-sidra-4714", force=True)
    assert run.status == "failed"
    assert "incompatível" in (run.error or "")


def test_unknown_transformer_and_dtb_without_period(env: Env) -> None:
    bad = env.catalog.datasets["ibge-dtb"].model_copy(update={"silver": {"transformer": "nope"}})
    env.catalog.datasets["ibge-dtb"] = bad
    with pytest.raises(Exception, match="desconhecida"):
        env.builder.build("ibge-dtb")
