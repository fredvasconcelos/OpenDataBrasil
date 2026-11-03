"""Publicação controlada: release vigente, preservação do anterior e leitura fixada."""

from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from odb_catalog import PostgresAdvisoryLock, PublicationError, PublicationService, TableVersion
from odb_common.storage import LakehouseLayout, Layer
from odb_lakehouse import DeltaReader, DeltaWriter
from odb_query_engine import DuckDBConfig, DuckDBReadEngine, PinnedTable, ReadQuery
from tests.contracts.delta_interop.conftest import make_frame
from tests.support import duckdb_extension_directory

pytestmark = pytest.mark.integration


class FlakyVerifier:
    """Aprova as primeiras ``ok_calls`` verificações e reprova as seguintes."""

    def __init__(self, ok_calls: int) -> None:
        self.calls = 0
        self.ok_calls = ok_calls

    def has_version(self, table_uri: str, version: int) -> bool:
        self.calls += 1
        return self.calls <= self.ok_calls


@pytest.fixture
def layout(tmp_path: Path) -> LakehouseLayout:
    return LakehouseLayout(tmp_path.as_uri())


@pytest.fixture
def table_uri(layout: LakehouseLayout, engine: Engine) -> str:
    uri = layout.table_uri(Layer.GOLD, "demo", "fact_obs")
    writer = DeltaWriter(layout, PostgresAdvisoryLock(engine))
    writer.write(uri, make_frame([1]), run_id="r0")  # v0: 1 linha
    writer.write(uri, make_frame([2]), run_id="r1")  # v1: 2 linhas
    writer.write(uri, make_frame([3]), run_id="r2")  # v2: 3 linhas
    return uri


@pytest.fixture
def service(engine: Engine) -> PublicationService:
    return PublicationService(engine, DeltaReader(), actor="pytest")


def _tv(uri: str, version: int, quality: str = "passed") -> TableVersion:
    return TableVersion("demo.fact_obs", uri, version, "1.0.0", quality)  # type: ignore[arg-type]


def _publish(service: PublicationService, uri: str, version: int) -> str:
    release_id = service.create_draft("demo", "test-sha", [_tv(uri, version)])
    service.validate(release_id)
    service.activate(release_id)
    return release_id


def test_lifecycle_supersedes_previous(service: PublicationService, table_uri: str) -> None:
    assert service.active("demo") is None
    first = _publish(service, table_uri, 0)
    assert service.resolve("demo", "demo.fact_obs").delta_version == 0
    second = _publish(service, table_uri, 1)
    active = service.active("demo")
    assert active is not None
    assert active.release_id == second
    assert active.manifest["tables"][0]["delta_version"] == 1
    old = service.get(first)
    assert old.status == "superseded"
    assert old.manifest["tables"][0]["delta_version"] == 0  # reprodutível


def test_validation_failure_keeps_previous_active(
    service: PublicationService, table_uri: str
) -> None:
    current = _publish(service, table_uri, 1)
    for bad in (_tv(table_uri, 99), _tv(table_uri, 2, quality="failed")):
        release_id = service.create_draft("demo", "test-sha", [bad])
        with pytest.raises(PublicationError, match="validação falhou"):
            service.validate(release_id)
        assert service.get(release_id).status == "failed"
        assert service.get(release_id).failure_reason
    active = service.active("demo")
    assert active is not None
    assert active.release_id == current


def test_activation_failure_rolls_back(engine: Engine, table_uri: str) -> None:
    good = PublicationService(engine, DeltaReader(), actor="pytest")
    current = _publish(good, table_uri, 1)

    # Validação aprova, mas a reverificação dentro da transação de ativação falha
    # (por exemplo, arquivos removidos entre as duas etapas).
    flaky = PublicationService(engine, FlakyVerifier(ok_calls=1), actor="pytest")
    release_id = flaky.create_draft("demo", "test-sha", [_tv(table_uri, 2)])
    flaky.validate(release_id)
    with pytest.raises(PublicationError, match="ativação abortada"):
        flaky.activate(release_id)

    active = good.active("demo")
    assert active is not None
    assert active.release_id == current  # anterior preservado
    assert good.get(current).status == "active"
    assert good.get(release_id).status == "failed"
    with engine.connect() as conn:
        events = (
            conn.execute(
                text(
                    "SELECT to_status FROM publication.release_event WHERE release_id = :id "
                    "ORDER BY event_id"
                ),
                {"id": release_id},
            )
            .scalars()
            .all()
        )
    assert events == ["draft", "validated", "failed"]


def test_invalid_transitions(service: PublicationService, table_uri: str) -> None:
    release_id = service.create_draft("demo", "sha", [_tv(table_uri, 0)])
    with pytest.raises(PublicationError, match="validados"):
        service.activate(release_id)
    assert service.get(release_id).status == "draft"
    service.validate(release_id)
    with pytest.raises(PublicationError, match="draft"):
        service.validate(release_id)
    with pytest.raises(PublicationError, match="inexistente"):
        service.activate("00000000-0000-0000-0000-000000000000")
    with pytest.raises(PublicationError, match="inexistente"):
        service.get("00000000-0000-0000-0000-000000000000")
    with pytest.raises(PublicationError, match="ao menos uma"):
        service.create_draft("demo", "sha", [])
    with pytest.raises(PublicationError, match="repetido"):
        service.create_draft("demo", "sha", [_tv(table_uri, 0), _tv(table_uri, 1)])
    with pytest.raises(PublicationError, match="nenhum release ativo"):
        service.resolve("other", "demo.fact_obs")
    _publish(service, table_uri, 0)
    with pytest.raises(PublicationError, match="não publicada"):
        service.resolve("demo", "demo.missing")


def test_duckdb_reads_published_version_not_latest(
    service: PublicationService, table_uri: str, layout: LakehouseLayout, tmp_path: Path
) -> None:
    """O consumo resolve a versão no catálogo e nunca lê a mais recente implicitamente."""
    _publish(service, table_uri, 1)
    pinned = service.resolve("demo", "demo.fact_obs")
    config = DuckDBConfig(
        memory_limit="512MB",
        threads=2,
        temp_directory=str(tmp_path / "duck"),
        extension_directory=duckdb_extension_directory(),
    )
    with DuckDBReadEngine(config, [layout.layer_uri(Layer.GOLD)]) as engine:
        result = engine.execute(
            ReadQuery(
                "SELECT count(*) FROM {{fact}}",
                {"fact": PinnedTable(pinned.storage_uri, pinned.delta_version)},
            )
        )
    assert result.rows == [(2,)]  # v1, embora a tabela esteja na v2
    assert DeltaReader().current_version(table_uri) == 2
