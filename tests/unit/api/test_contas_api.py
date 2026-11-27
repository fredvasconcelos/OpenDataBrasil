"""Rotas /api/v1/contas sobre a Gold das contas construída com a Silver simulada."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import polars as pl
import pytest
from fastapi.testclient import TestClient

from odb_api.app import create_app
from odb_api.config import ApiSettings
from odb_api.contas import ContasService
from odb_api.deps import ApiDeps
from odb_api.gold import GoldGateway
from odb_api.release import ReleaseResolver
from odb_catalog.publication import Release, TableVersion
from odb_lakehouse import DeltaReader
from odb_modeling import contas
from odb_modeling.builder import GoldTable
from odb_modeling.contas import recipient_id
from odb_modeling.contas_locations import FACT_EXECUTION_LOCATION, execution_locations
from odb_query_engine import DuckDBConfig, DuckDBReadEngine
from tests.support import duckdb_extension_directory
from tests.unit.modeling.test_contas_gold import GoldContas

ATLAS = recipient_id("50875450000104", "ATLAS LTDA")
PERSON = recipient_id("***.810.079-**", "FULANA DE TAL")


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    tmp = tmp_path_factory.mktemp("contas-api")
    env = GoldContas(tmp)
    build = env.builder.build()
    assert build.status == "succeeded", build.error
    source = env.registry.silver_success(env.builder.datasets()["execution"])
    assert source is not None
    assert source.delta_version is not None
    located = execution_locations(
        DeltaReader().scan(source.target_uri, source.delta_version),
        contas.Dimensions(
            recipient=pl.DataFrame(),
            management_unit=env.table(build, "dim_management_unit"),
            budget_action=env.table(build, "dim_budget_action"),
            expense_nature=env.table(build, "dim_expense_nature"),
            amendment_author=env.table(build, "dim_amendment_author"),
        ),
    )
    contract = FACT_EXECUTION_LOCATION
    uri = env.builder.table_uri(contract.name)
    result = env.env.builder._writer.write(
        uri, located, run_id=build.build_id, mode="error", partition_by=contract.partition_by
    )
    build.tables[contract.name] = GoldTable(contract.name, uri, result.version, contract.version)
    release = Release(
        release_id="contas-1",
        scope="contas",
        status="validated",
        code_version="test",
        manifest={},
        tables={
            t: TableVersion(t, g.storage_uri, g.delta_version, g.contract_version, "passed")
            for t, g in build.tables.items()
        },
        activated_at=datetime(2026, 11, 22, tzinfo=UTC),
    )
    duck = DuckDBReadEngine(
        DuckDBConfig(
            memory_limit="512MB",
            threads=2,
            temp_directory=str(tmp / "duck"),
            extension_directory=duckdb_extension_directory(),
        ),
        [env.env.layout.root_uri + "/gold"],
    )
    gold = GoldGateway(duck)
    resolver = ReleaseResolver(lambda: release, ttl_s=0)
    deps = ApiDeps(
        settings=ApiSettings(rate_limit_per_minute=0, response_cache_mb=8),
        resolver=resolver,  # o painel não é usado nestes testes
        gold=gold,
        kpis=None,  # type: ignore[arg-type]
        catalog=None,  # type: ignore[arg-type]
        engine=duck,
        contas=ContasService(gold, resolver),
        closers=[duck],
    )
    with TestClient(create_app(deps)) as c:
        yield c


def _get(client: TestClient, path: str, status: int = 200) -> Any:
    response = client.get(path)
    assert response.status_code == status, response.text
    return response.json()


def test_meta_lists_lenses_months_and_status(client: TestClient) -> None:
    meta = _get(client, "/api/v1/contas/meta")
    assert meta["release_id"] == "contas-1"
    lenses = {lens["lens"]: lens for lens in meta["lenses"]}
    assert lenses["A"]["periods"] == ["2024M10", "2024M11"]
    assert [s["status"] for s in lenses["A"]["statuses"]] == ["fechado", "aberto"]
    assert "function" in {d["id"] for d in lenses["A"]["dimensions"]}
    assert {"territory", "recipient"} <= {d["id"] for d in lenses["B"]["group_by"]}


def test_map_totals_by_state_and_flags_the_open_month(client: TestClient) -> None:
    out = _get(client, "/api/v1/contas/map?lens=A&level=uf&periods=2024")
    assert {r["geography_key"]: r["value"] for r in out["rows"]} == {
        "uf:25": pytest.approx(2 * 2001.85),
        "uf:51": pytest.approx(-24.0),
    }
    assert out["provenance"]["partial"] is True
    assert [n["period"] for n in out["provenance"]["period_notes"]] == ["2024M11"]
    october = _get(client, "/api/v1/contas/map?lens=A&level=municipio&within=uf:25&periods=2024M10")
    assert [(r["name"], r["value"]) for r in october["rows"]] == [("Guarabira", 2001.0)]
    assert october["provenance"]["partial"] is False


def test_detail_by_dimension_sums_chosen_categories(client: TestClient) -> None:
    out = _get(
        client,
        "/api/v1/contas/map?lens=A&level=uf&periods=2024M10"
        "&dimension=recipient_class&categories=estado_df",
    )
    assert [(r["geography_key"], r["value"]) for r in out["rows"]] == [("uf:25", 0.85)]
    comp = _get(
        client,
        "/api/v1/contas/composition?lens=A&geography_key=uf:25&periods=2024M10"
        "&dimension=recipient_class",
    )
    assert [(r["label"], r["value"]) for r in comp["rows"]] == [
        ("Municípios (prefeituras)", 2001.0),
        ("Estados e Distrito Federal", 0.85),
    ]


def test_series_by_month(client: TestClient) -> None:
    out = _get(client, "/api/v1/contas/series?lens=B&geography_key=uf:24")
    assert out["lines"][0]["points"] == [
        {"period": "2024M10", "value": 700.0},
        {"period": "2024M11", "value": 700.0},
    ]


def test_ranking_shows_names_only_and_the_homonym_note(client: TestClient) -> None:
    out = _get(client, "/api/v1/contas/ranking?lens=B&geography_key=brasil:1&year=2024")
    assert [r["recipient"]["name"] for r in out["rows"]] == [None, "ATLAS LTDA", "FULANA DE TAL"]
    assert out["total_recipients"] == 3
    assert out["pages"] == 1
    assert out["notes"]  # há pessoa física: aviso de homônimo
    body = str(out)
    assert "50875450000104" not in body  # sem CNPJ
    assert "***" not in body  # sem CPF mascarado


def test_table_groups_by_territory_and_by_recipient(client: TestClient) -> None:
    states = _get(client, "/api/v1/contas/table?lens=B&geography_key=regiao:2&periods=2024M10")
    assert [(r["key"], r["value"]) for r in states["rows"]] == [
        ("uf:25", 356964.30),
        ("uf:24", 700.0),
    ]
    assert states["rows_total"] == 2
    people = _get(
        client,
        "/api/v1/contas/table?lens=B&geography_key=brasil:1&periods=2024M10&group_by=recipient",
    )
    # Banco e sigiloso fora; o exterior entra.
    assert [r["label"] for r in people["rows"]] == [
        "(sem nome na fonte)",
        "ATLAS LTDA",
        "FULANA DE TAL",
    ]
    everyone = _get(
        client,
        "/api/v1/contas/table?lens=B&geography_key=brasil:1&periods=2024M10"
        "&group_by=recipient&include_intermediaries=true&sort=name",
    )
    assert everyone["rows_total"] == 5
    filtered = _get(
        client,
        "/api/v1/contas/table?lens=A&geography_key=brasil:1&periods=2024M10"
        "&group_by=recipient_class&filter=transfer_type:Constitucionais e Royalties",
    )
    assert filtered["value_total"] == pytest.approx(1989.85)


def test_invalid_requests_are_422(client: TestClient) -> None:
    for path in (
        "/api/v1/contas/table?lens=A&group_by=drop_table",
        "/api/v1/contas/table?lens=A&filter=organ",
        "/api/v1/contas/table?lens=A&geography_key=municipio:2506301&group_by=territory",
        "/api/v1/contas/map?lens=B&dimension=function",
        "/api/v1/contas/map?periods=2019",
        "/api/v1/contas/table?page=101",
        "/api/v1/contas/busca?q=ab",
    ):
        assert client.get(path).status_code == 422, path


def test_recipient_profile_and_noindex_for_people(client: TestClient) -> None:
    company = client.get(f"/api/v1/contas/favorecidos/{ATLAS}?periods=2024")
    assert company.status_code == 200, company.text
    assert "x-robots-tag" not in company.headers
    body = company.json()
    assert body["recipient"]["seat_municipality"] == "GUARABIRA"
    assert {(t["lens"], t["year"]) for t in body["totals"]} == {("B", 2024)}
    person = client.get(f"/api/v1/contas/favorecidos/{PERSON}?periods=2024")
    assert person.headers["x-robots-tag"] == "noindex, nofollow"
    assert person.json()["notes"]
    cached = client.get(f"/api/v1/contas/favorecidos/{PERSON}?periods=2024")
    assert cached.headers["x-odb-cache"] == "hit"
    assert cached.headers["x-robots-tag"] == "noindex, nofollow"  # o cache preserva
    assert client.get("/api/v1/contas/favorecidos/0000000000000000").status_code == 404


def test_search_finds_companies_but_not_people(client: TestClient) -> None:
    hits = _get(client, "/api/v1/contas/busca?q=atlas")["hits"]
    assert [(h["kind"], h["id"]) for h in hits] == [("favorecido", ATLAS)]
    assert not _get(client, "/api/v1/contas/busca?q=fulana")["hits"]


def test_execution_phases(client: TestClient) -> None:
    out = _get(client, "/api/v1/contas/execucao?periods=2024M10&dimension=action")
    assert out["total"]["paid"] == pytest.approx(743598.53)
    assert out["rows"][0]["payables_paid"] == pytest.approx(27426.73)


def test_responses_carry_the_contas_release_and_are_cached(client: TestClient) -> None:
    first = client.get("/api/v1/contas/ranking?lens=A")
    second = client.get("/api/v1/contas/ranking?lens=A")
    assert first.headers["x-odb-release"] == "contas-1"
    assert first.headers["x-odb-cache"] == "miss"
    assert second.headers["x-odb-cache"] == "hit"


def test_execucao_preserva_totais_em_pagina_sem_linhas(client: TestClient) -> None:
    primeira = _get(client, "/api/v1/contas/execucao?periods=2024M10&dimension=action")
    distante = _get(client, "/api/v1/contas/execucao?periods=2024M10&dimension=action&page=100")
    assert distante["rows"] == []
    assert distante["total"] == primeira["total"]
    assert distante["rows_total"] == primeira["rows_total"]
    assert distante["pages"] == primeira["pages"]
    vazio = _get(
        client,
        "/api/v1/contas/execucao?periods=2024M10&dimension=action&filter=function:inexistente",
    )
    assert vazio["rows_total"] == 0
    assert vazio["total"]["paid"] == 0


def test_execucao_anuncia_localizador_quando_presente_e_reconcilia_total(
    client: TestClient,
) -> None:
    meta = _get(client, "/api/v1/contas/meta")
    c = next(lens for lens in meta["lenses"] if lens["lens"] == "C")
    assert {"localizer", "localizer_uf", "localizer_municipality"} <= {
        d["id"] for d in c["dimensions"]
    }
    base = _get(client, "/api/v1/contas/execucao?periods=2024M10&dimension=action")
    located = _get(client, "/api/v1/contas/execucao?periods=2024M10&dimension=localizer")
    assert located["total"] == base["total"]
    assert "fact_federal_execution_location" in {
        t["table_id"] for t in located["provenance"]["tables"]
    }
    uf = _get(client, "/api/v1/contas/execucao?periods=2024M10&dimension=localizer_uf")
    assert uf["total"] == base["total"]
    if uf["rows"]:
        code = uf["rows"][0]["category_code"]
        filtered = _get(
            client,
            f"/api/v1/contas/execucao?periods=2024M10&dimension=localizer_municipality&filter=localizer_uf:{code}",
        )
        assert filtered["total"]["paid"] == uf["rows"][0]["paid"]
