import json
from pathlib import Path

import httpx
import pytest

from odb_common.storage import LakehouseLayout
from odb_ingestion import BronzeStore, HttpClient, IngestionRunner, build_connectors, load_sources
from odb_ingestion.contract import BaseConnector
from tests.ingestion_support import TEST_SOURCES, FakeSources, InMemoryRegistry, fixture_bytes


class Env:
    def __init__(self, tmp_path: Path) -> None:
        self.catalog = load_sources(TEST_SOURCES)
        self.fake = FakeSources()
        self.registry = InMemoryRegistry()
        self.bronze = BronzeStore(LakehouseLayout((tmp_path / "lake").as_uri()))
        self.capacity_error: Exception | None = None

        def capacity() -> None:
            if self.capacity_error:
                raise self.capacity_error

        def factory(connector: BaseConnector) -> HttpClient:
            return HttpClient(
                connector.source.http, transport=self.fake.transport(), sleep=lambda _s: None
            )

        self.runner = IngestionRunner(
            self.catalog,
            build_connectors(self.catalog),
            self.bronze,
            self.registry,
            factory,
            capacity_check=capacity,
        )

    def bronze_files(self) -> list[Path]:
        return sorted(p for p in self.bronze.bronze_root.rglob("*") if p.is_file())


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def test_first_run_stores_all_partitions(env: Env) -> None:
    report = env.runner.run("ibge-sidra-6579", run_id=None)
    assert report.status == "succeeded", report.error
    assert report.planned == 22
    assert report.counts == {"stored": 22}
    assert report.bytes_stored == report.bytes_downloaded > 0
    files = env.bronze_files()
    assert len(files) == 22
    assert all("/ibge-sidra/ibge-sidra-6579/" in str(f) for f in files)
    stored = env.registry.by_status("stored")
    assert {a.reference_period for a in stored} >= {"2024", "2025"}
    assert all(a.license_id == "ibge-reuso-com-citacao" for a in stored)
    assert all(a.access_classification == "public_conditional" for a in stored)
    assert len(env.registry.watermarks["ibge-sidra-6579"]) == 22
    ingestion = env.registry.ingestions[report.ingestion_id]
    assert ingestion["status"] == "succeeded"
    assert len(ingestion["plan"]["requests"]) == 22
    assert not list((env.bronze.bronze_root.parent / "tmp" / "ingestion").glob("*/*"))


def test_rerun_does_not_duplicate_bytes(env: Env) -> None:
    env.runner.run("ibge-sidra-6579")
    files_before = env.bronze_files()
    second = env.runner.run("ibge-sidra-6579")
    assert second.status == "succeeded"
    assert second.planned == 2  # só a janela de revisão (2025, 2026)
    assert second.counts == {"reused": 2}
    assert second.bytes_stored == 0
    assert env.bronze_files() == files_before
    reused = env.registry.by_status("reused")
    originals = {a.artifact_id: a for a in env.registry.by_status("stored")}
    for r in reused:
        assert originals[r.reused_from].checksum_sha256 == r.checksum_sha256  # type: ignore[index]
        assert r.storage_uri == originals[r.reused_from].storage_uri  # type: ignore[index]
    full = env.runner.run("ibge-sidra-6579", full=True)
    assert full.counts == {"reused": 22}
    assert env.bronze_files() == files_before


def test_revised_content_is_stored_as_new_version(env: Env) -> None:
    env.runner.run("ibge-sidra-6579")
    payload = json.loads(fixture_bytes("t6579_n1n2n3_p2025.json"))
    payload[1]["V"] = "1751951"  # revisão de um valor
    env.fake.overrides["/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2025"] = lambda _r: (
        httpx.Response(200, content=json.dumps(payload).encode())
    )
    report = env.runner.run("ibge-sidra-6579")
    assert report.counts == {"stored": 1, "reused": 1}
    assert len(env.bronze_files()) == 23  # versão anterior preservada


def test_invalid_response_is_quarantined_and_ingestion_fails(env: Env) -> None:
    env.fake.overrides["/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2026"] = lambda _r: (
        httpx.Response(200, content=fixture_bytes("t6579_n3_p1900_empty.json"))
    )
    report = env.runner.run("ibge-sidra-6579")
    assert report.status == "failed"
    assert report.counts["quarantined"] == 1
    assert report.counts["stored"] == 21
    assert "quarentena" in (report.error or "")
    q = env.registry.by_status("quarantined")[0]
    assert "/quarantine/" in (q.storage_uri or "")
    assert not q.validation["valid"]
    assert "ibge-sidra-6579" not in env.registry.watermarks  # watermark não avança


def test_http_failure_isolated_per_dataset(env: Env) -> None:
    env.fake.overrides["/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2003"] = lambda _r: (
        httpx.Response(503)
    )
    reports = env.runner.run_many(["ibge-sidra-6579", "ibge-sidra-4714", "ibge-dtb"])
    assert [r.status for r in reports] == ["failed", "succeeded", "succeeded"]
    failed = env.registry.by_status("failed")
    assert len(failed) == 1
    assert failed[0].http_status == 503
    assert failed[0].partition_key == "n1n2n3-p2003"
    assert len(env.registry.synced) == 1


def test_plan_failure_marks_ingestion_failed(env: Env) -> None:
    env.fake.overrides["/values/t/6579/n1/all/v/9324/p/all"] = lambda _r: httpx.Response(404)
    report = env.runner.run("ibge-sidra-6579")
    assert report.status == "failed"
    assert "404" in (report.error or "")
    assert env.registry.ingestions[report.ingestion_id]["status"] == "failed"


def test_conditional_request_not_modified(env: Env) -> None:
    first = env.runner.run("ibge-dtb")
    assert first.counts == {"stored": 1}
    assert env.registry.watermarks["ibge-dtb"]["file"].etag == '"dtb-v1"'
    second = env.runner.run("ibge-dtb")
    assert second.counts == {"not_modified": 1}
    assert second.bytes_downloaded == 0
    assert env.fake.requests[-1].headers["if-none-match"] == '"dtb-v1"'
    stored = env.registry.by_status("stored")[0]
    assert stored.source_version == "Thu, 26 Mar 2026 21:07:36 GMT"


def test_disk_block_and_disabled_dataset(env: Env) -> None:
    env.capacity_error = RuntimeError("disco cheio")
    assert "disco cheio" in (env.runner.run("ibge-dtb").error or "")
    env.capacity_error = None
    disabled = env.catalog.datasets["ibge-dtb"].model_copy(update={"enabled": False})
    env.catalog.datasets["ibge-dtb"] = disabled
    assert "desabilitado" in (env.runner.run("ibge-dtb").error or "")
    assert env.bronze_files() == []


def test_concurrent_duplicate_is_resolved_as_reuse(env: Env) -> None:
    env.registry.fail_next_store_with_duplicate = True
    report = env.runner.run("ibge-dtb")
    assert report.status == "succeeded"
    assert report.counts == {"reused": 1}
    assert env.bronze_files() == []  # cópia própria removida; bytes do "outro processo" valem
    assert env.registry.by_status("reused")[0].reused_from == "concurrent"


def test_plan_only(env: Env) -> None:
    plan = env.runner.plan("ibge-sidra-4714")
    assert [r.partition_key for r in plan.requests] == ["n1n2n3-p2022"]
    assert env.bronze_files() == []
