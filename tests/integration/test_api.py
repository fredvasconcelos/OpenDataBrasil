"""API com PostgreSQL real (papel ``odb_reader``) sobre um release publicado pela CLI."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from typer.testing import CliRunner

from odb_api.app import create_app
from odb_api.config import ApiSettings
from odb_api.deps import ApiDeps, _NoVerifier
from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService
from odb_api.portal import load_portal
from odb_api.release import ReleaseResolver
from odb_api.repository import CatalogRepository
from odb_catalog.publication import PublicationService
from odb_cli.main import app as cli
from odb_query_engine import DuckDBConfig, DuckDBReadEngine
from tests.integration.test_gold import lake  # noqa: F401 - fixture reaproveitada
from tests.support import duckdb_extension_directory

pytestmark = pytest.mark.integration
PORTAL = Path(__file__).resolve().parents[2] / "configs" / "portal"


def test_api_with_reader_role(lake: Path, reader_engine: Engine, tmp_path: Path) -> None:  # noqa: F811
    runner = CliRunner()
    assert runner.invoke(cli, ["ingest", "run", "--all"]).exit_code == 0
    assert runner.invoke(cli, ["silver", "build", "--all"]).exit_code == 0
    built = runner.invoke(cli, ["gold", "build", "--activate"])
    assert built.exit_code == 0, built.output

    duck = DuckDBReadEngine(
        DuckDBConfig(
            memory_limit="512MB",
            threads=2,
            temp_directory=str(tmp_path / "duck-api"),
            extension_directory=duckdb_extension_directory(),
        ),
        [(lake / "gold").as_uri()],
    )
    publication = PublicationService(reader_engine, _NoVerifier(), actor="api")
    gold = GoldGateway(duck)
    settings = ApiSettings(portal_config_dir=str(PORTAL), rate_limit_per_minute=0)
    deps = ApiDeps(
        settings=settings,
        resolver=ReleaseResolver(lambda: publication.active("demografia"), ttl_s=0),
        gold=gold,
        kpis=KpiService(gold, load_portal(PORTAL, "demografia"), page_max=100),
        catalog=CatalogRepository(reader_engine),
        engine=duck,
        closers=[duck],
    )
    with TestClient(create_app(deps)) as client:
        health = client.get("/health").json()
        active = publication.active("demografia")
        assert active is not None
        assert health == {"status": "ok", "release_id": active.release_id}
        sources = client.get("/api/v1/sources").json()
        assert {s["source_id"] for s in sources} == {"ibge-sidra", "ibge-geoftp"}
        dataset = client.get("/api/v1/datasets/ibge-sidra-9606").json()
        assert dataset["license"]["review_status"] == "requires_review"
        assert len(client.get("/api/v1/datasets").json()) == 15
        mapped = client.get("/api/v1/kpis/pessoas_quilombolas/map?level=uf").json()
        assert len(mapped["values"]) == 27
        assert mapped["provenance"]["release_id"] == active.release_id
        exported = client.post(
            "/api/v1/exports",
            json={"kpi_id": "pessoas_quilombolas", "level": "uf", "format": "json"},
        ).json()
        assert exported["metadata"]["fonte"]["dataset_id"] == "ibge-sidra-8176"
