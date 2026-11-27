"""API sobre uma Gold construída com fixtures reais (e malhas sintéticas)."""

from __future__ import annotations

import dataclasses
import gzip
import io
import json
import re
import shutil
import tempfile
import tomllib
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from odb_api import kpis as kpi_module
from odb_api.app import create_app
from odb_api.config import ApiSettings
from odb_api.deps import ApiDeps
from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService
from odb_api.middleware import RateLimiter
from odb_api.release import ReleaseContext, ReleaseResolver, ReleaseUnavailableError
from odb_api.schemas import NavigationOut
from odb_catalog.publication import Release, TableVersion
from odb_query_engine import DuckDBConfig, DuckDBReadEngine
from odb_semantics import PanoramaConfigError, SemanticError, load_panorama
from odb_semantics.portal import (
    PortalConfigError,
    check_against_release,
    load_portal,
    release_problems,
)
from tests.gold_support import GoldEnv
from tests.support import duckdb_extension_directory

REPO = Path(__file__).resolve().parents[3]
# Só o portal curado: a Gold de teste tem as tabelas das fixtures. Os fragmentos
# gerados do panorama dependem da Gold real (conferidos em test_panorama_gen).
PORTAL_DIR = Path(tempfile.mkdtemp(prefix="odb-portal-"))
shutil.copy(REPO / "configs" / "portal" / "demografia.toml", PORTAL_DIR)
PANORAMA_REPO = REPO / "configs" / "catalog" / "panorama.toml"
# Os itens `externos` (Sinesp, ADR-0012) apontam para KPIs de outra Silver, ausente da
# Gold de teste: o panorama de teste não os traz (conferidos em test_external_kpis...).
PANORAMA = Path(tempfile.mkdtemp(prefix="odb-panorama-")) / "panorama.toml"
# Ligações explícitas a KPIs de fragmentos curados (POF de 1987 e 1995, ADR-0016) também
# saem: o portal de teste só tem o arquivo principal.
FRAGMENT_KPIS = (
    "ipca",
    "nivel_instrucao_capitais",
    "aquisicao_alimentar",
    "pof_despesa_alimentacao_antiga",
    "pof_despesa_distribuicao_antiga",
    "pof_recebimento_distribuicao_antiga",
    # Séries compostas de fontes distintas (ADR-0022), fragmento compostas.toml.
    "alfabetizacao_serie",
    "esgotamento_serie",
    "lixo_serie",
    # Mês como calendário (gerados pelo panorama, fora do portal de teste).
    "obitos_mensal",
    "casamentos_mensal",
    # As novas medidas têm fragmento próprio e são validadas com dados nativos.
    *(
        item["id"]
        for item in tomllib.loads((REPO / "configs/catalog/medidas-adicionais.toml").read_text())[
            "measures"
        ]
        if item["publish"]
    ),
    *(
        item["id"]
        for item in tomllib.loads((REPO / "configs/catalog/medidas-agro.toml").read_text())[
            "measures"
        ]
        if item["publish"]
    ),
)
_panorama_text = re.sub(
    r"\nexternos = \[.*?\n\]\n", "\n", PANORAMA_REPO.read_text(encoding="utf-8"), flags=re.S
)
for _kpi in FRAGMENT_KPIS:
    # A receita N2 usa chaves TOML entre aspas; as duas grafias são equivalentes.
    # O portal reduzido de fixtures precisa retirar os vínculos em ambas.
    _panorama_text = re.sub(
        r',\s*(?:"kpi"|kpi)\s*=\s*"' + re.escape(_kpi) + '"', "", _panorama_text
    )
PANORAMA.write_text(_panorama_text, encoding="utf-8")


class FakeCatalog:
    """Catálogo operacional em memória (``down`` simula o PostgreSQL fora do ar)."""

    down = False

    def _check(self) -> None:
        if self.down:
            raise OperationalError("SELECT 1", {}, Exception("failed to resolve host 'postgres'"))

    def sources(self) -> list[dict[str, Any]]:
        self._check()
        return [
            {
                "source_id": "ibge-sidra",
                "institution_id": "ibge",
                "name": "SIDRA",
                "connector_type": "sidra",
                "base_url": "https://apisidra.ibge.gov.br",
                "documentation_url": None,
            }
        ]

    def datasets(self, dataset_id: str | None = None) -> list[dict[str, Any]]:
        row = {
            "dataset_id": "ibge-sidra-9606",
            "source_id": "ibge-sidra",
            "official_id": "9606",
            "title": "Cor ou raça e sexo",
            "description": "teste",
            "periodicity": "decenal",
            "reference_url": "https://sidra.ibge.gov.br/tabela/9606",
            "access_classification": "public_conditional",
            "license_id": "ibge-reuso-com-citacao",
            "license_name": "Reuso com citação",
            "license_url": None,
            "conditions": "citar o IBGE",
            "review_status": "requires_review",
        }
        return [row] if dataset_id in {None, "ibge-sidra-9606"} else []

    def ping(self) -> None:
        self._check()


def _release(env: GoldEnv, release_id: str = "rel-1") -> Release:
    build = env.gold.build()
    assert build.status in {"succeeded", "skipped"}, build.error
    return Release(
        release_id=release_id,
        scope="demografia",
        status="active",
        code_version="test",
        manifest={},
        tables={
            t: TableVersion(t, g.storage_uri, g.delta_version, g.contract_version, "passed")
            for t, g in build.tables.items()
        },
        activated_at=datetime(2026, 11, 6, tzinfo=UTC),
    )


@pytest.fixture(scope="module")
def stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    tmp = tmp_path_factory.mktemp("api")
    env = GoldEnv(tmp)
    env.prepare()
    state = {"release": _release(env)}
    duck = DuckDBReadEngine(
        DuckDBConfig(
            memory_limit="512MB",
            threads=2,
            temp_directory=str(tmp / "duck"),
            extension_directory=duckdb_extension_directory(),
        ),
        [env.layout.root_uri + "/gold"],
    )
    gold = GoldGateway(duck)
    settings = ApiSettings(portal_config_dir=str(PORTAL_DIR), rate_limit_per_minute=0)
    catalog = FakeCatalog()
    deps = ApiDeps(
        settings=settings,
        resolver=ReleaseResolver(lambda: state["release"], ttl_s=0),
        gold=gold,
        kpis=KpiService(
            gold,
            load_portal(PORTAL_DIR, "demografia"),
            page_max=1000,
            panorama=load_panorama(PANORAMA),
        ),
        catalog=catalog,  # type: ignore[arg-type]
        engine=duck,
        closers=[duck],
    )
    with TestClient(create_app(deps)) as client:
        yield {"client": client, "state": state, "env": env, "gold": gold, "catalog": catalog}


def _get(stack: dict[str, Any], path: str, status: int = 200) -> Any:
    response = stack["client"].get(path)
    assert response.status_code == status, response.text
    return response.json()


def test_acumulado_sazonal_recusa_populacao_sem_alterar_a_serie(stack: dict[str, Any]) -> None:
    body = _get(
        stack,
        "/api/v1/kpis/populacao_estimada/seasonal?geography=brasil:1&year_from=2023&year_to=2025",
        422,
    )
    assert body["error"]["code"] == "semantic_rule"
    meta = _get(stack, "/api/v1/kpis/populacao_estimada")
    assert not meta["temporal"]["seasonal_sum"]
    assert meta["temporal"]["isolate"]


def test_catalog_down_is_503_and_recovers(stack: dict[str, Any]) -> None:
    # Ex.: o PostgreSQL não voltou depois de um reinício do Docker. Sem traceback
    # (500): 503 com nova tentativa, e a API volta sozinha quando o banco volta.
    stack["catalog"].down = True
    try:
        for path in ("/health", "/api/v1/sources"):
            response = stack["client"].get(path)
            assert response.status_code == 503, response.text
            assert response.json()["error"]["code"] == "catalog_unavailable"
            assert response.headers["Retry-After"] == "1"
    finally:
        stack["catalog"].down = False
    assert _get(stack, "/health")["status"] == "ok"


def test_health_release_and_catalog(stack: dict[str, Any]) -> None:
    assert _get(stack, "/health") == {
        "status": "ok",
        "release_id": "rel-1",
        "portal": "ok",
        "unavailable_kpis": {},
    }
    release = _get(stack, "/api/v1/release")
    assert release["release_id"] == "rel-1"
    assert {t["table_id"] for t in release["tables"]} >= {"indicator_observation", "dim_geometry"}
    assert _get(stack, "/api/v1/sources")[0]["source_id"] == "ibge-sidra"
    assert _get(stack, "/api/v1/datasets/ibge-sidra-9606")["license"]["review_status"] == (
        "requires_review"
    )
    _get(stack, "/api/v1/datasets/nao-existe", 404)
    found = _get(stack, "/api/v1/indicators?q=quilombolas")
    assert "censo_pessoas_quilombolas_sexo" in {i["indicator_id"] for i in found}
    ind = _get(stack, "/api/v1/indicators/censo_populacao_cor_raca_sexo")
    assert ind["periods"] == ["2010", "2022"]
    assert _get(stack, "/api/v1/indicators/tree")[0]["depth"] == 0
    response = stack["client"].get("/api/v1/release")
    assert response.headers["x-odb-release"] == "rel-1"


def test_navigation_lists_mvp_kpis(stack: dict[str, Any]) -> None:
    nav = _get(stack, "/api/v1/portal/navigation")
    assert nav["dimension_order"] == [
        "c86",
        "c2",
        "sexosim",
        "sexosinesp",
        "c287",
        "c58",
        "c1",
        "c2661",
        "c1714",
        "c339",
        "c12190",
    ]
    kpis = {k["kpi_id"]: k for t in nav["themes"] for s in t["subthemes"] for k in s["kpis"]}
    pop = kpis["populacao_residente"]
    assert [d["classification_id"] for d in pop["dimensions"]] == ["c86", "c2", "c287"]
    assert [c["name"] for c in pop["dimensions"][1]["categories"]] == ["Homens", "Mulheres"]
    # Fixtures sem nível municipal: o mapa só tem os níveis com valores e geometria.
    assert pop["map_levels"] == ["brasil", "regiao", "uf"]
    assert kpis["indigenas_em_terras_indigenas"]["source"]["source_table_id"] == "9954"
    assert _get(stack, "/api/v1/kpis/pessoas_quilombolas")["unit"] == "Pessoas"


def test_indice_preserva_ordem_busca_e_release(stack: dict[str, Any]) -> None:
    client = stack["client"]
    nav = _get(stack, "/api/v1/portal/navigation")
    response = client.get("/api/v1/portal/index")
    index = response.json()
    expected = {
        **nav,
        "themes": [
            {
                **theme,
                "subthemes": [
                    {
                        **sub,
                        "kpis": [
                            {
                                **{
                                    key: item[key]
                                    for key in ("kpi_id", "label", "name", "description")
                                },
                                "source_table_id": item["source"]["source_table_id"],
                            }
                            for item in sub["kpis"]
                        ],
                    }
                    for sub in theme["subthemes"]
                ],
            }
            for theme in nav["themes"]
        ],
    }
    assert index == expected
    assert len(response.content) < len(client.get("/api/v1/portal/navigation").content)
    assert response.headers["x-odb-release"] == nav["release_id"]
    assert response.headers["cache-control"] == "public, max-age=60"
    cached = client.get("/api/v1/portal/index", headers={"If-None-Match": response.headers["etag"]})
    assert cached.status_code == 304
    assert not cached.content
    original = stack["state"]["release"]
    try:
        stack["state"]["release"] = dataclasses.replace(original, release_id="indice-outro-release")
        changed = client.get(
            "/api/v1/portal/index", headers={"If-None-Match": response.headers["etag"]}
        )
        assert changed.status_code == 200
        assert changed.json()["release_id"] == "indice-outro-release"
        assert changed.headers["etag"] != response.headers["etag"]
    finally:
        stack["state"]["release"] = original


def test_geometria_reutiliza_gzip_e_negocia_variantes(
    stack: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    compress = gzip.compress

    def counted(*args: Any, **kwargs: Any) -> bytes:
        nonlocal calls
        calls += 1
        return compress(*args, **kwargs)

    # gold usa gzip.compress pelo módulo: trocar no próprio gzip (sem reexportar).
    monkeypatch.setattr(gzip, "compress", counted)
    client = stack["client"]
    path = "/api/v1/geometries/uf?within=brasil:1"
    plain = client.get(path, headers={"Accept-Encoding": "identity"})
    zipped = client.get(path, headers={"Accept-Encoding": "gzip"})
    assert plain.status_code == zipped.status_code == 200
    assert plain.content == zipped.content  # httpx descomprime automaticamente.
    assert "content-encoding" not in plain.headers
    assert zipped.headers["content-encoding"] == "gzip"
    assert "Accept-Encoding" in plain.headers["vary"]
    assert "Accept-Encoding" in zipped.headers["vary"]
    assert plain.headers["etag"] != zipped.headers["etag"]
    assert calls == 1
    for encoding in ("gzip;q=0, *;q=1", "gzip;q=ruim", "", "br"):
        response = client.get(path, headers={"Accept-Encoding": encoding})
        assert response.content == plain.content
        assert "content-encoding" not in response.headers
    wildcard = client.get(path, headers={"Accept-Encoding": "*;q=0.5"})
    assert wildcard.headers["content-encoding"] == "gzip"
    cached = client.get(
        path, headers={"Accept-Encoding": "gzip", "If-None-Match": zipped.headers["etag"]}
    )
    assert cached.status_code == 304
    assert not cached.content
    assert calls == 1


def test_pivot_recusa_por_contagem_antes_de_materializar(
    stack: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(kpi_module, "PIVOT_MAX_CELLS", 1)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("a recusa deve acontecer antes de transportar as observações")

    monkeypatch.setattr(KpiService, "_observations", forbidden)
    response = stack["client"].get(
        "/api/v1/kpis/populacao_residente/pivot?level=uf&rows=territorio&cols=periodo"
    )
    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "semantic_rule",
        "message": "tabela dinâmica grande demais (mais de 1 células): "
        "escolha um nível maior, um recorte ou menos campos",
    }
    assert response.headers["x-odb-release"] == stack["state"]["release"].release_id


def test_detalhes_em_lote_equivalem_a_rota_individual_com_uma_leitura(
    stack: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    original = KpiService._observations

    def counted(self: KpiService, *args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(KpiService, "_observations", counted)
    client = stack["client"]
    path = "/api/v1/kpis/populacao_residente"
    batch = client.get(path + "/details?level=uf&period=2022&dimensions=c2")
    assert batch.status_code == 200, batch.text
    assert calls == 1
    assert batch.json()
    for item in batch.json():
        individual = client.get(
            path + "/detail",
            params={
                "geography": item["geography"]["geography_key"],
                "period": "2022",
                "dimensions": "c2",
            },
        )
        assert individual.status_code == 200
        single = individual.json()
        assert {k: v for k, v in item.items() if k != "provenance"} == {
            k: v for k, v in single.items() if k != "provenance"
        }
        # O pedido individual usa a ponte territorial para isolar o território;
        # o lote nacional filtra diretamente pelo nível. A linhagem preserva isso.
        assert item["provenance"]["release_id"] == single["provenance"]["release_id"]
        assert item["provenance"]["truncated"] is False
    refused = client.get(path + "/details?level=municipio&period=2022")
    assert refused.status_code == 422


def test_exportacao_com_varios_niveis_respeita_periodos_por_grao(stack: dict[str, Any]) -> None:
    client = stack["client"]
    body = {
        "kpi_id": "populacao_residente",
        "level": "uf",
        "levels": ["regiao", "uf"],
        "periods_by_grain": {"ano": ["2010"]},
        "format": "json",
    }
    response = client.post("/api/v1/exports", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["rows"]
    assert {row["periodo"] for row in data["rows"]} == {"2010"}
    assert {row["nivel"] for row in data["rows"]} == {"regiao", "uf"}
    assert data["metadata"]["filtros"]["periods_by_grain"] == {"ano": ["2010"]}
    invalid = client.post(
        "/api/v1/exports", json={**body, "periods_by_grain": {"mes": ["2010M01"]}}
    )
    assert invalid.status_code == 422


def test_opcoes_exportacao_contam_territorios_do_recorte(stack: dict[str, Any]) -> None:
    client = stack["client"]
    path = "/api/v1/kpis/populacao_residente/export-options"
    country = client.get(path)
    region = client.get(path + "?within=regiao:2")
    assert country.status_code == region.status_code == 200
    data = region.json()
    territories = client.get("/api/v1/geographies?level=uf&within=regiao:2&limit=500").json()
    assert data["territory_counts"]["uf"] == len(territories)
    assert data["territory_counts"]["uf"] < country.json()["territory_counts"]["uf"]
    assert data["within"] == "regiao:2"
    assert data["release_id"] == stack["state"]["release"].release_id
    assert data["max_rows"] > 0


def test_navigation_follows_panorama(stack: dict[str, Any]) -> None:
    nav = _get(stack, "/api/v1/portal/navigation")
    themes = {t["theme_id"]: t for t in nav["themes"]}
    assert len(themes) == 20
    assert sum(len(t["subthemes"]) for t in themes.values()) == 64
    pop = {s["subtheme_id"]: s for s in themes["populacao"]["subthemes"]}
    # Publicados no lugar do panorama, na ordem do panorama; o resto planejado.
    assert [k["kpi_id"] for k in pop["tamanho_crescimento"]["kpis"]] == [
        "populacao_estimada",
        "populacao_residente",
        "area_territorial",
        "densidade_demografica",
    ]
    planned = pop["tamanho_crescimento"]["planned"]
    assert [p["kpi_id"] for p in planned] == ["crescimento_populacional", "populacao_nos_censos"]
    assert planned[0]["source_table_id"] == "4709"
    # Temas sem dados publicados: só planejados; filtros adaptados ao tema.
    agro = themes["agropecuaria"]
    assert all(not s["kpis"] for s in agro["subthemes"])
    assert {f["filter_id"] for f in agro["filters"]} == {"produto", "especie"}
    assert "cor_raca" in {f["filter_id"] for f in themes["populacao"]["filters"]}
    published = [k["kpi_id"] for t in nav["themes"] for s in t["subthemes"] for k in s["kpis"]]
    # 13 com `kpi` explícito e a 9605, ligada pelo id do item (populacao_cor_raca_censos).
    assert len(published) == 14
    assert "populacao_cor_raca_censos" in published


def test_periodo_padrao_respeita_cobertura_do_nivel(
    stack: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduz POF e séries Censo + PNAD: o último ano global não existe em todo nível."""
    gold: GoldGateway = stack["gold"]
    ctx = ReleaseContext(stack["state"]["release"])
    coverage = {**gold.periods_by_level(ctx)}
    coverage["populacao_estimada"] = {**coverage["populacao_estimada"], "uf": ["2024"]}
    monkeypatch.setattr(gold, "periods_by_level", lambda _: coverage)
    service = KpiService(gold, load_portal(PORTAL_DIR, "demografia"), page_max=100)
    deps = dataclasses.replace(stack["client"].app.state.deps, kpis=service, closers=[])
    with TestClient(create_app(deps)) as client:
        meta = client.get("/api/v1/kpis/populacao_estimada").json()
        assert meta["periods"][-1] > "2024"
        assert meta["periods_by_level"]["uf"] == ["2024"]
        for route in ("map?level=uf", "table?level=uf", "detail?geography=uf:29"):
            response = client.get(f"/api/v1/kpis/populacao_estimada/{route}")
            assert response.status_code == 200, response.text
            assert response.json()["period"] == "2024"
        # Um pedido explícito indisponível é recusado, sem trocar o ano solicitado.
        response = client.get("/api/v1/kpis/populacao_estimada/map?level=uf&period=2025")
        assert response.status_code == 422
        assert "no nível uf" in response.json()["error"]["message"]


def test_panorama_must_cover_portal(tmp_path: Path, stack: dict[str, Any]) -> None:
    text = PANORAMA.read_text(encoding="utf-8")
    path = tmp_path / "panorama.toml"
    # Sem `kpi` e com outro id, o item deixa de ligar o KPI do portal.
    orphaned = text.replace(', kpi = "populacao_estimada"', "", 1).replace(
        'id = "populacao_estimada"', 'id = "populacao_estimada_antiga"', 1
    )
    path.write_text(orphaned, encoding="utf-8")
    portal = load_portal(PORTAL_DIR, "demografia")
    with pytest.raises(PanoramaConfigError, match="fora do panorama"):
        KpiService(stack["gold"], portal, page_max=10, panorama=load_panorama(path))


def test_map_detail_series_and_table(stack: dict[str, Any]) -> None:
    mapped = _get(stack, "/api/v1/kpis/populacao_residente/map?level=uf")
    assert mapped["period"] == "2022"
    assert len(mapped["values"]) == 27
    bahia = next(v for v in mapped["values"] if v["geography_key"] == "uf:29")
    assert bahia["value"] == 14141626

    detail = _get(
        stack, "/api/v1/kpis/populacao_residente/detail?geography=uf:29&dimensions=c2,c86"
    )
    assert detail["dimensions"] == ["c86", "c2"]  # ordem fixa do portal
    root = detail["root"]
    assert (root["label"], root["value"], root["share_pct"]) == ("Total", 14141626, 100.0)
    parda = next(c for c in root["children"] if c["label"] == "Parda")
    assert (parda["value"], parda["share_pct"]) == (8103964, 57.31)
    assert [(c["label"], c["value"], c["share_pct"]) for c in parda["children"]] == [
        ("Homens", 3911184, 48.26),
        ("Mulheres", 4192780, 51.74),
    ]
    assert any("Indígena" in n for n in detail["notes"])
    only_sex = _get(stack, "/api/v1/kpis/populacao_residente/detail?geography=uf:29&dimensions=c2")
    assert [c["label"] for c in only_sex["root"]["children"]] == ["Homens", "Mulheres"]
    plain = _get(stack, "/api/v1/kpis/populacao_residente/detail?geography=uf:29")
    assert plain["root"]["children"] == []

    series = _get(stack, "/api/v1/kpis/populacao_residente/series?geography=brasil:1&dimensions=c2")
    assert [s["label"] for s in series["series"]] == ["Total", "Homens", "Mulheres"]
    # O portal tira do gráfico a série de profundidade 0 (Total) quando há detalhe.
    assert [s["depth"] for s in series["series"]] == [0, 1, 1]
    assert series["series"][0]["points"] == [
        {
            "period": "2010",
            "value": 190755799,
            "status": "valid",
            "source_table_id": "9606",
            "share_pct": 100,
            "share_base_value": 190755799,
        },
        {
            "period": "2022",
            "value": 203080756,
            "status": "valid",
            "source_table_id": "9606",
            "share_pct": 100,
            "share_base_value": 203080756,
        },
    ]
    assert series["share_methods"] == ["published_total"]

    table = _get(stack, "/api/v1/kpis/pessoas_quilombolas/table?level=uf&dimensions=c2&limit=27")
    assert [c["label"] for c in table["columns"]] == ["Total", "Homens", "Mulheres"]
    assert table["total_rows"] == 27
    totals = [r["cells"]["c2:6794"]["value"] for r in table["rows"]]
    assert totals == sorted(totals, reverse=True)
    assert table["rows"][0]["name"] == "Bahia"
    cells = table["rows"][0]["cells"]
    assert cells["c2:4"]["value"] + cells["c2:5"]["value"] == cells["c2:6794"]["value"]
    page = _get(
        stack,
        "/api/v1/kpis/pessoas_quilombolas/table?level=uf&sort=name&order=asc&limit=2&offset=1",
    )
    assert [r["name"] for r in page["rows"]] == ["Alagoas", "Amapá"]
    assert "uf_abbreviation" in page["rows"][0]  # siglas vêm dos municípios (sem N6 aqui)
    # locate: a página que contém o território, na mesma ordenação (clique no mapa).
    base = "/api/v1/kpis/pessoas_quilombolas/table?level=uf&sort=name&order=asc&limit=5"
    everything = _get(stack, base.replace("limit=5", "limit=27"))
    position = [r["geography_key"] for r in everything["rows"]].index("uf:52")
    located = _get(stack, base + "&offset=0&locate=uf:52")
    assert located["offset"] == position // 5 * 5
    assert "uf:52" in [r["geography_key"] for r in located["rows"]]
    # Fora da tabela (outro nível): vale o offset pedido.
    assert _get(stack, base + "&offset=10&locate=regiao:1")["offset"] == 10


def test_table_matrix_groups_row_totals_and_footer(stack: dict[str, Any]) -> None:
    """Matriz (DS 2.3.9): grupos da 1ª dimensão, totais de linha e linha de totais."""
    table = _get(
        stack, "/api/v1/kpis/populacao_residente/table?level=uf&dimensions=c86,c2&limit=27"
    )
    cols = table["columns"]
    total = cols[0]
    assert (total["label"], total["depth"], total["parent"]) == ("Total", 0, None)
    assert total["group"] == total["key"]
    # Totais de linha: Total da cor ou raça por sexo, logo depois do Total.
    assert [c["label"] for c in cols[1:3]] == ["Homens", "Mulheres"]
    assert all(c["group"] == total["key"] and c["parent"] == total["key"] for c in cols[1:3])
    # Cada cor ou raça é um grupo, com o sexo dentro; o pai é o grupo.
    heads = [c for c in cols if c["depth"] == 1 and c["group"] == c["key"]]
    assert heads
    inner = [c for c in cols if c["depth"] == 2]
    assert inner
    assert all(c["parent"] == c["group"] for c in inner)
    # Rodapé: o Brasil, com o valor publicado (e não a soma das UFs).
    footer = table["footer"]
    assert footer["geography_key"] == "brasil:1"
    assert footer["cells"][total["key"]]["value"] == 203080756
    within = _get(stack, "/api/v1/kpis/populacao_residente/table?level=uf&within=regiao:2&limit=27")
    assert within["footer"]["geography_key"] == "regiao:2"
    assert _get(stack, "/api/v1/kpis/populacao_residente/table?level=brasil")["footer"] is None


def test_non_additive_kpi_has_no_shares(stack: dict[str, Any]) -> None:
    detail = _get(stack, "/api/v1/kpis/percentual_indigenas/detail?geography=uf:13")
    assert detail["additivity"] == "non_additive"
    assert detail["root"]["share_pct"] is None
    kpi = _get(stack, "/api/v1/kpis/percentual_indigenas")
    assert kpi["category_shares"] is False  # taxa em %: sem % das categorias
    error = _get(
        stack, "/api/v1/kpis/percentual_indigenas/detail?geography=uf:13&dimensions=c2", 422
    )
    assert error["error"]["code"] == "semantic_rule"


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/api/v1/kpis/nao_existe/map?level=uf", 404, "not_found"),
        ("/api/v1/kpis/populacao_residente/map?level=terra_indigena", 422, "semantic_rule"),
        ("/api/v1/kpis/populacao_residente/map?level=uf&period=1999", 422, "semantic_rule"),
        ("/api/v1/kpis/populacao_residente/detail?geography=uf;drop", 422, "invalid_request"),
        ("/api/v1/kpis/populacao_residente/detail?geography=uf:99", 404, "not_found"),
        ("/api/v1/geometries/terra_indigena", 404, "not_found"),
        ("/api/v1/geographies/x", 422, "invalid_request"),
    ],
)
def test_errors(stack: dict[str, Any], path: str, status: int, code: str) -> None:
    assert _get(stack, path, status)["error"]["code"] == code


def test_geographies_and_geometry(stack: dict[str, Any]) -> None:
    found = _get(stack, "/api/v1/geographies?q=sao%20paulo&level=uf")
    assert [g["geography_key"] for g in found] == ["uf:35"]
    within = _get(stack, "/api/v1/geographies?level=uf&within=regiao:2&limit=100")
    assert len(within) == 9
    assert _get(stack, "/api/v1/geographies/uf:29")["name"] == "Bahia"
    response = stack["client"].get("/api/v1/geometries/uf")
    assert response.headers["content-type"] == "application/geo+json"
    collection = response.json()
    assert len(collection["features"]) == 27
    assert collection["metadata"]["release_id"] == "rel-1"
    etag = response.headers["etag"]
    cached = stack["client"].get("/api/v1/geometries/uf", headers={"If-None-Match": etag})
    assert cached.status_code == 304
    nordeste = stack["client"].get("/api/v1/geometries/uf?within=regiao:2").json()
    assert len(nordeste["features"]) == 9


def test_query_endpoint_applies_semantic_rules(stack: dict[str, Any]) -> None:
    client = stack["client"]
    ok = client.post(
        "/api/v1/query",
        json={"indicators": ["censo_pessoas_quilombolas_sexo"], "level": "uf", "limit": 5},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["has_more"] is True
    assert len(body["rows"]) == 5
    assert body["provenance"]["derived"] is False
    derived = client.post(
        "/api/v1/query",
        json={"indicators": ["censo_pessoas_quilombolas_sexo"], "level": "uf", "sum_to": "brasil"},
    ).json()
    assert derived["provenance"]["derived"] is True
    assert derived["rows"][0]["value_status"] == "derived_sum"
    for payload, fragment in [
        (
            {"indicators": ["censo_percentual_indigenas"], "level": "uf", "sum_to": "brasil"},
            "não aditivos",
        ),
        (
            {
                "indicators": ["censo_pessoas_indigenas", "censo_populacao_cor_raca_sexo"],
                "level": "uf",
            },
            "não podem ser combinados",
        ),
    ]:
        rejected = client.post("/api/v1/query", json=payload)
        assert rejected.status_code == 422
        assert fragment in rejected.json()["error"]["message"]
    sql = client.post("/api/v1/query", json={"sql": "select 1", "indicators": ["x"], "level": "uf"})
    assert sql.status_code == 422


def test_dicionarios_expoem_fichas_apoios_e_candidatas_sem_ativacao(stack: dict[str, Any]) -> None:
    index = _get(stack, "/api/v1/dictionaries")
    assert len(index["entries"]) == 335
    assert len(index["expansions"]) == 50
    assert index["preparation"]["total"] == 50
    entry = _get(stack, "/api/v1/dictionaries/nascidos_vivos")
    assert entry["document"]["lacunas"]
    assert entry["methods"][0]["id"] == "M04"
    assert entry["documentary_status"] == "revisao_parcial"
    _get(stack, "/api/v1/dictionaries/inexistente", 404)


def test_exportacao_de_marginais_conserva_todos_os_filtros_e_blocos(
    stack: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deps = stack["client"].app.state.deps
    cfg = deps.kpis.kpi(deps.resolver.current(), "populacao_residente")
    monkeypatch.setattr(
        deps.kpis, "kpi", lambda *_args: cfg.model_copy(update={"exclusive_dimensions": True})
    )
    response = stack["client"].post(
        "/api/v1/exports",
        json={
            "kpi_id": "populacao_residente",
            "level": "uf",
            "format": "json",
            "dimensions": ["c86", "c2"],
            "categories": ["c86:2779"],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metadata"]["filtros"]["dimensions"] == ["c86", "c2"]
    assert payload["metadata"]["filtros"]["categories"] == ["c86:2779"]
    assert len(payload["metadata"]["blocos"]) == 2
    assert {row["block_id"] for row in payload["rows"]} == {"bloco-1", "bloco-2"}
    assert len({row["row_id"] for row in payload["rows"]}) == len(payload["rows"])


def test_exports_carry_metadata(stack: dict[str, Any]) -> None:
    client = stack["client"]
    payload = {"kpi_id": "populacao_residente", "level": "uf", "dimensions": ["c86", "c2"]}
    csv = client.post("/api/v1/exports", json=payload | {"format": "csv"})
    assert csv.status_code == 200, csv.text
    assert 'filename="populacao_residente_uf.zip"' in csv.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(csv.content)) as archive:
        rows = archive.read("dados.csv").decode("utf-8-sig").splitlines()
        meta = json.loads(archive.read("metadados.json"))
    assert rows[0].startswith(
        "row_id,geography_key,territorio,uf,periodo,Cor ou raça,Sexo,valor,status,unidade,"
    )
    assert "value_exact" in rows[0]
    assert "c86_code" in rows[0]
    # 27 UFs x 2 censos x (Total + 5 cores ou raças) x (Total + 2 sexos)
    assert len(rows) - 1 == meta["linhas"] == 27 * 2 * 6 * 3
    assert meta["release"]["release_id"] == "rel-1"
    assert meta["fonte"]["license_id"] == "ibge-reuso-com-citacao"
    parquet = client.post("/api/v1/exports", json=payload | {"format": "parquet"})
    frame = pl.read_parquet(io.BytesIO(parquet.content))
    assert frame.schema["valor"] == pl.Int64
    xlsx = client.post("/api/v1/exports", json=payload | {"format": "xlsx"})
    assert pl.read_excel(io.BytesIO(xlsx.content), sheet_name="dados").height == 972
    as_json = client.post("/api/v1/exports", json=payload | {"format": "json"}).json()
    assert as_json["metadata"]["kpi"]["kpi_id"] == "populacao_residente"
    too_big = stack["client"].app.state.deps
    original = too_big.settings
    too_big.settings = original.model_copy(update={"export_max_rows": 10})
    try:
        refused = client.post("/api/v1/exports", json=payload)
        assert refused.status_code == 413
    finally:
        too_big.settings = original
    # Teste de carga de 2026-11-17: o motor cortava no próprio teto (duckdb_max_rows) e a
    # exportação saía com 200 e o arquivo incompleto. Agora o corte do motor também é 413.
    engine = too_big.engine
    config = engine._config
    engine._config = dataclasses.replace(config, export_max_rows=10)
    try:
        cut = client.post("/api/v1/exports", json=payload)
        assert cut.status_code == 413, cut.text
        assert cut.json()["error"]["code"] == "too_large"
    finally:
        engine._config = config


@pytest.mark.parametrize(
    ("kpi_id", "size", "status"),
    [
        ("safra_estimada", 200_000, 200),
        ("safra_estimada", 200_001, 413),
        ("safra_area_colhida", 200_000, 200),
        ("safra_area_colhida", 200_001, 413),
        *[
            (f"pib_municipios_v{variable}", 100_001, 413)
            for variable in (498, 513, 516, 525, 543, 6575)
        ],
    ],
)
def test_teto_maior_restrito_aos_dois_kpis_lspa(
    stack: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    kpi_id: str,
    size: int,
    status: int,
) -> None:
    """O limite conta linhas do arquivo, aceita a borda e recusa excedentes sem cortar."""
    deps: ApiDeps = stack["client"].app.state.deps
    ctx = deps.resolver.current()
    cfg, dims, obs, prov = deps.kpis.export_rows(
        ctx,
        "populacao_residente",
        level="uf",
        periods=[],
        within=None,
        dimensions=[],
        max_rows=100_000,
    )
    # A fixture usa observações reais do Censo para isolar a política de tamanho;
    # a LSPA real é conferida separadamente na candidata, sem ativação.
    cfg = cfg.model_copy(update={"id": kpi_id})
    monkeypatch.setattr(deps.kpis, "kpi", lambda *_args: cfg)

    def export_rows(*_args: Any, **_kwargs: Any) -> Any:
        return cfg, dims, [obs[0]] * size, prov

    monkeypatch.setattr(deps.kpis, "export_rows", export_rows)
    response = stack["client"].post(
        "/api/v1/exports",
        json={"kpi_id": kpi_id, "level": "uf", "format": "parquet"},
    )
    assert response.status_code == status, response.text[:500] if status != 200 else ""
    if status == 200:
        assert pl.read_parquet(io.BytesIO(response.content)).height == size
    else:
        assert response.json()["error"]["code"] == "too_large"


def test_teto_lspa_conta_o_total_de_todos_os_niveis(
    stack: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duas partes permitidas isoladamente não podem somar mais de 200 mil no arquivo."""
    deps: ApiDeps = stack["client"].app.state.deps
    ctx = deps.resolver.current()
    cfg, dims, obs, prov = deps.kpis.export_rows(
        ctx,
        "populacao_residente",
        level="uf",
        periods=[],
        within=None,
        dimensions=[],
        max_rows=100_000,
    )
    cfg = cfg.model_copy(update={"id": "safra_estimada"})
    monkeypatch.setattr(deps.kpis, "kpi", lambda *_args: cfg)
    monkeypatch.setattr(
        deps.kpis, "export_rows", lambda *_args, **_kw: (cfg, dims, [obs[0]] * 100_001, prov)
    )
    response = stack["client"].post(
        "/api/v1/exports",
        json={"kpi_id": "safra_estimada", "level": "uf", "levels": ["uf", "brasil"]},
    )
    assert response.status_code == 413
    assert "200.000" in response.json()["error"]["message"]


def test_openapi_documents_routes(stack: dict[str, Any]) -> None:
    spec = _get(stack, "/openapi.json")
    paths = set(spec["paths"])
    assert {
        "/api/v1/portal/navigation",
        "/api/v1/kpis/{kpi_id}/map",
        "/api/v1/kpis/{kpi_id}/detail",
        "/api/v1/kpis/{kpi_id}/series",
        "/api/v1/kpis/{kpi_id}/table",
        "/api/v1/exports",
        "/api/v1/query",
        "/api/v1/geometries/{level}",
    } <= paths
    # Nenhuma rota recebe SQL ou caminho de arquivo.
    assert not [p for p in paths if "sql" in p or "path" in p]


def test_new_release_is_used_without_restart(stack: dict[str, Any]) -> None:
    state = stack["state"]
    previous = state["release"]
    state["release"] = dataclasses.replace(previous, release_id="rel-2")
    try:
        assert _get(stack, "/health")["release_id"] == "rel-2"
        mapped = _get(stack, "/api/v1/kpis/populacao_residente/map?level=regiao")
        assert mapped["provenance"]["release_id"] == "rel-2"
    finally:
        state["release"] = previous


def test_resolver_keeps_last_release_when_catalog_fails() -> None:
    calls = {"n": 0}
    release = Release("r", "demografia", "active", "t", {})

    def load() -> Release | None:
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("postgres fora do ar")
        return release

    now = {"t": 0.0}
    resolver = ReleaseResolver(load, ttl_s=5, clock=lambda: now["t"])
    assert resolver.current().release_id == "r"
    now["t"] = 10.0
    assert resolver.current().release_id == "r"  # falha usa o release em cache
    with pytest.raises(ReleaseUnavailableError):
        ReleaseResolver(lambda: None, ttl_s=5).current()
    with pytest.raises(ReleaseUnavailableError):
        ReleaseResolver(lambda: (_ for _ in ()).throw(RuntimeError()), ttl_s=5).current()


def test_rate_limiter() -> None:
    now = {"t": 0.0}
    limiter = RateLimiter(2, clock=lambda: now["t"])
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    now["t"] = 30.0  # recarga de 1 ficha a cada 30 s
    assert limiter.allow("a")
    assert RateLimiter(0).allow("x")


def test_navigation_is_built_once_per_release(
    stack: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = stack["client"]
    first = client.get("/api/v1/portal/navigation")
    assert first.status_code == 200
    calls = {"n": 0}
    original = KpiService.navigation

    def counted(self: KpiService, ctx: Any) -> Any:
        calls["n"] += 1
        return original(self, ctx)

    monkeypatch.setattr(KpiService, "navigation", counted)
    again = client.get("/api/v1/portal/navigation")
    assert again.content == first.content
    assert calls["n"] == 0  # do cache do release
    # Mesmo JSON que o response_model produziria.
    nav = NavigationOut.model_validate(first.json())
    assert first.json() == nav.model_dump(mode="json", by_alias=True)
    # ETag por release: 304 sem corpo.
    etag = first.headers["etag"]
    assert stack["state"]["release"].release_id in etag
    cached = client.get("/api/v1/portal/navigation", headers={"If-None-Match": etag})
    assert cached.status_code == 304
    assert not cached.content
    # /kpis/{id} devolve o item da navegação, sem remontar a navegação.
    item = nav.themes[0].subthemes[0].kpis[0]
    one = client.get(f"/api/v1/kpis/{item.kpi_id}")
    assert one.json() == item.model_dump(mode="json", by_alias=True)
    assert calls["n"] == 0
    assert client.get("/api/v1/kpis/nao_existe").status_code == 404


def test_client_ip_only_trusts_forwarded_from_proxies() -> None:
    import ipaddress  # noqa: PLC0415

    from odb_api.middleware import client_ip  # noqa: PLC0415

    rede = [ipaddress.ip_network("172.30.0.0/24")]
    # Pelo portal (proxy confiável): vale o último IP, o que o Caddy anotou.
    assert client_ip("172.30.0.5", "203.0.113.9", rede) == "203.0.113.9"
    # Cliente tentando forjar: só o último elemento conta.
    assert client_ip("172.30.0.5", "1.1.1.1, 203.0.113.9", rede) == "203.0.113.9"
    # Conexão direta de fora da rede confiável: o cabeçalho é ignorado.
    assert client_ip("198.51.100.7", "1.1.1.1", rede) == "198.51.100.7"
    # Sem proxies configurados (padrão): sempre o IP da conexão.
    assert client_ip("172.30.0.5", "203.0.113.9", []) == "172.30.0.5"
    # Lixo no cabeçalho: cai para o IP da conexão.
    assert client_ip("172.30.0.5", "<script>", rede) == "172.30.0.5"
    assert client_ip(None, "203.0.113.9", rede) == "unknown"


def test_portal_config_is_checked(tmp_path: Path, stack: dict[str, Any]) -> None:
    text = (PORTAL_DIR / "demografia.toml").read_text(encoding="utf-8")
    # A ordem dos detalhes é a do KPI; uma dimensão fora de dimension_order é erro.
    unknown = text.replace('dimension_order = ["c86", "c2",', 'dimension_order = ["c2",')
    (tmp_path / "demografia.toml").write_text(unknown, encoding="utf-8")
    with pytest.raises(PortalConfigError, match="fora de dimension_order"):
        load_portal(tmp_path, "demografia")
    (tmp_path / "outro.toml").write_text(text, encoding="utf-8")
    with pytest.raises(PortalConfigError, match="difere"):
        load_portal(tmp_path, "outro")
    with pytest.raises(PortalConfigError, match="inválida"):
        load_portal(tmp_path, "inexistente")
    config = load_portal(PORTAL_DIR, "demografia")
    ctx = ReleaseContext(stack["state"]["release"])
    gold: GoldGateway = stack["gold"]
    indicators, partitions = gold.indicators(ctx), gold.partitions(ctx)
    check_against_release(config, indicators, partitions)
    with pytest.raises(PortalConfigError, match="não publicado"):
        check_against_release(config, {}, partitions)
    with pytest.raises(PortalConfigError, match="partição"):
        check_against_release(config, indicators, {"c86": [], "c2": []})


def test_inconsistent_kpi_is_hidden_not_the_portal(tmp_path: Path, stack: dict[str, Any]) -> None:
    """ADR-0015: um KPI fora do release sai da navegação; o resto do portal segue no ar.

    Reproduz 2026-11-12: release novo sem o indicador que a configuração antiga da
    API ainda citava. Antes, a navegação inteira respondia 500.
    """
    text = (PORTAL_DIR / "demografia.toml").read_text(encoding="utf-8")
    marker = 'indicator = "populacao_estimada"\n'
    assert marker in text
    (tmp_path / "demografia.toml").write_text(
        text.replace(marker, 'indicator = "indicador_retirado"\n', 1), encoding="utf-8"
    )
    service = KpiService(
        stack["gold"],
        load_portal(tmp_path, "demografia"),
        page_max=100,
        panorama=load_panorama(PANORAMA),
    )
    # Sem closers: o motor DuckDB é o do módulo, compartilhado com os outros testes.
    deps = dataclasses.replace(stack["client"].app.state.deps, kpis=service, closers=[])
    with TestClient(create_app(deps)) as client:
        nav = client.get("/api/v1/portal/navigation")
        assert nav.status_code == 200, nav.text
        subthemes = [s for t in nav.json()["themes"] for s in t["subthemes"]]
        published = [k["kpi_id"] for s in subthemes for k in s["kpis"]]
        planned = [p["kpi_id"] for s in subthemes for p in s["planned"]]
        assert "populacao_estimada" not in published
        assert "populacao_estimada" not in planned  # some; não vira "planejado"
        assert len(published) == 13
        assert "populacao_residente" in published
        missing = client.get("/api/v1/kpis/populacao_estimada")
        assert missing.status_code == 404
        assert "indisponível no release" in missing.json()["error"]["message"]
        assert client.get("/api/v1/kpis/populacao_residente/map?level=uf").status_code == 200
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["portal"] == "degraded"
        assert health.json()["unavailable_kpis"] == {
            "populacao_estimada": ["indicador indicador_retirado não publicado no release"]
        }


def test_release_problems_by_kpi(stack: dict[str, Any]) -> None:
    """A conferência devolve os problemas por KPI, inclusive a tabela do panorama."""
    config = load_portal(PORTAL_DIR, "demografia")
    ctx = ReleaseContext(stack["state"]["release"])
    gold: GoldGateway = stack["gold"]
    indicators, partitions = gold.indicators(ctx), gold.partitions(ctx)
    panorama = load_panorama(PANORAMA)
    assert release_problems(config, indicators, partitions, panorama) == {}
    kpi = config.kpi("populacao_residente")
    assert kpi is not None
    changed = {
        **indicators,
        kpi.indicator: {**indicators[kpi.indicator], "source_table_id": "9999"},
    }
    problems = release_problems(config, changed, partitions, panorama)
    # Os dois KPIs da 9606 usam o mesmo indicador.
    assert list(problems) == ["populacao_residente", "populacao_sexo_idade"]
    assert problems["populacao_residente"][0].startswith("tabela ")
    assert problems["populacao_residente"][0].endswith(", 9999 na Gold")


def test_concurrent_requests_are_consistent(stack: dict[str, Any]) -> None:
    """Consultas simultâneas (§11.5): todas respondem, com os mesmos valores."""
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

    paths = [
        "/api/v1/kpis/populacao_residente/map?level=uf",
        "/api/v1/kpis/populacao_residente/detail?geography=uf:29&dimensions=c86,c2",
        "/api/v1/kpis/pessoas_quilombolas/table?level=uf&dimensions=c2",
        "/api/v1/geometries/regiao",
    ] * 8
    client = stack["client"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(client.get, paths))
    assert {r.status_code for r in responses} == {200}
    bodies: dict[str, set[str]] = {}
    for path, response in zip(paths, responses, strict=True):
        bodies.setdefault(path, set()).add(response.text)
    assert all(len(v) == 1 for v in bodies.values())


def test_category_filter_recomputes_everything(stack: dict[str, Any]) -> None:
    """Detalhar por como filtro (DS 2.4): mapa, tooltip, série e tabela na seleção."""
    url = "/api/v1/kpis/populacao_residente"
    full = _get(stack, f"{url}/detail?geography=uf:29&dimensions=c86")
    keys = {c["label"]: c["category_key"] for c in full["root"]["children"]}
    parda, preta = keys["Parda"], keys["Preta"]
    values = {c["label"]: c["value"] for c in full["root"]["children"]}
    chosen = f"{parda},{preta}"

    detail = _get(stack, f"{url}/detail?geography=uf:29&dimensions=c86&categories={chosen}")
    root = detail["root"]
    assert root["value"] == values["Parda"] + values["Preta"]  # Total = soma da seleção
    assert sorted(c["label"] for c in root["children"]) == ["Parda", "Preta"]
    assert round(sum(c["share_pct"] for c in root["children"]), 1) == 100.0

    mapped = _get(stack, f"{url}/map?level=uf&categories={chosen}")
    bahia = next(v for v in mapped["values"] if v["geography_key"] == "uf:29")
    assert bahia["value"] == root["value"]

    series = _get(stack, f"{url}/series?geography=uf:29&dimensions=c86&categories={parda}")
    assert [s["label"] for s in series["series"]] == ["Total", "Parda"]
    assert series["series"][0]["points"][-1]["value"] == values["Parda"]

    table = _get(stack, f"{url}/table?level=uf&dimensions=c86&categories={chosen}&limit=27")
    assert sorted(c["label"] for c in table["columns"]) == ["Parda", "Preta", "Total"]
    # Todas as categorias = sem filtro; categoria de outra dimensão = 422.
    every = ",".join(keys.values())
    assert _get(stack, f"{url}/map?level=uf&categories={every}") == _get(
        stack, f"{url}/map?level=uf"
    )
    _get(stack, f"{url}/map?level=uf&categories=c99:1", status=422)


def test_busy_engine_and_timeout_map_to_http(
    stack: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from odb_query_engine import QueryEngineBusyError, QueryTimeoutError  # noqa: PLC0415

    gold: GoldGateway = stack["gold"]
    for exc, status, code in [
        (QueryEngineBusyError("ocupado"), 503, "busy"),
        (QueryTimeoutError("lento"), 504, "timeout"),
    ]:

        def fail(*_args: Any, exc: Exception = exc, **_kwargs: Any) -> Any:
            raise exc

        monkeypatch.setattr(gold, "run_plan", fail)
        response = stack["client"].get("/api/v1/kpis/populacao_residente/map?level=uf")
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
    assert response.headers.get("retry-after") is None


def test_portal_fragment_extends_dimension_order(tmp_path: Path) -> None:
    import shutil as _sh  # noqa: PLC0415

    _sh.copy(PORTAL_DIR / "demografia.toml", tmp_path)
    (tmp_path / "demografia").mkdir()
    (tmp_path / "demografia" / "x.toml").write_text(
        'config_version = "1"\nscope = "demografia"\ndimension_order = ["c2", "c1480"]\n'
        '[[themes]]\nid = "gestao"\nlabel = "Gestão"\n[[themes.subthemes]]\nid = "plan"\n'
        'label = "Plan"\n[[themes.subthemes.kpis]]\nid = "plano_diretor"\nlabel = "P"\n'
        'indicator = "plano_diretor"\n'
        'dimensions = [{ classification = "c1480", partition = "p58278", label = "PD" }]\n',
        encoding="utf-8",
    )
    config = load_portal(tmp_path, "demografia")
    assert config.dimension_order[-1] == "c1480"
    assert config.dimension_order.count("c2") == 1
    assert config.kpi("plano_diretor") is not None


def test_map_share_of_a_category(tmp_path: Path, stack: dict[str, Any]) -> None:
    """KPI cujo Total é só o universo: o mapa mostra o % de uma categoria (map_share)."""
    text = (PORTAL_DIR / "demografia.toml").read_text(encoding="utf-8")
    marker = 'indicator = "censo_populacao_cor_raca_sexo"\n'
    assert marker in text
    (tmp_path / "demografia.toml").write_text(
        text.replace(marker, marker + 'map_share = "2776"\n', 1), encoding="utf-8"
    )
    portal = load_portal(tmp_path, "demografia")
    service = KpiService(stack["gold"], portal, page_max=100)
    ctx = ReleaseContext(stack["state"]["release"])
    out = service.map(ctx, "populacao_residente", level="uf", period="2022", within=None)
    assert out.measure == "share"
    assert out.unit == "%"
    assert out.measure_label == "% Branca"
    total = service.map(ctx, "populacao_estimada", level="uf", period=None, within=None)
    assert total.measure == "total"
    shares = [v.value for v in out.values if v.value is not None]
    assert shares
    assert all(0 < s < 100 for s in shares)
    # Sem dimensão, map_share é recusado na carga.
    bad = text.replace(
        'indicator = "populacao_estimada"\n',
        'indicator = "populacao_estimada"\nmap_share = "1"\n',
        1,
    )
    (tmp_path / "demografia.toml").write_text(bad, encoding="utf-8")
    with pytest.raises(PortalConfigError, match="map_share exige"):
        load_portal(tmp_path, "demografia")


def test_external_kpis_follow_the_panorama(tmp_path: Path, stack: dict[str, Any]) -> None:
    """Itens `externos` do panorama: precisam existir no portal e entram na navegação."""
    from odb_semantics.panorama import check_against_portal  # noqa: PLC0415

    panorama = load_panorama(PANORAMA_REPO)
    external = [e.kpi for t in panorama.temas for s in t.subtemas for e in s.externos]
    assert "sinesp_homicidio_doloso" in external
    portal = load_portal(REPO / "configs" / "portal", "demografia")
    portal_kpis = {k.id: k for k in portal.kpis()}
    check_against_portal(panorama, portal_kpis)  # todos ligados, nenhum órfão
    with pytest.raises(PanoramaConfigError, match="inexistentes no portal"):
        check_against_portal(
            panorama, {k: v for k, v in portal_kpis.items() if k != "sinesp_estupro"}
        )


def test_provenance_from_source_configuration() -> None:
    """Rodapé "Fonte": instituição e sistema de cada dataset, das fontes configuradas."""
    from odb_api.deps import provenance  # noqa: PLC0415
    from odb_ingestion.config import load_sources  # noqa: PLC0415

    out = provenance(load_sources(REPO / "configs" / "sources"))
    assert out["ibge-sidra-6579"] == ("IBGE", "SIDRA")
    assert out["mjsp-sinesp-vde"] == ("MJSP", None)
    assert out["datasus-sim-cid10-dores"] == ("MS", None)


def test_exclusive_dimensions_and_absent_categories(
    tmp_path: Path, stack: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-0016: dimensões marginais vão uma por vez; categoria sem dado não aparece."""
    text = (PORTAL_DIR / "demografia.toml").read_text(encoding="utf-8")
    marker = 'indicator = "censo_populacao_cor_raca_sexo"\n'
    assert marker in text
    (tmp_path / "demografia.toml").write_text(
        text.replace(marker, marker + "exclusive_dimensions = true\n", 1), encoding="utf-8"
    )
    service = KpiService(stack["gold"], load_portal(tmp_path, "demografia"), page_max=100)
    ctx = ReleaseContext(stack["state"]["release"])
    with pytest.raises(SemanticError, match="uma dimensão por vez"):
        service.series(ctx, "populacao_residente", geography="brasil:1", dimensions=["c86", "c2"])
    one = service.series(ctx, "populacao_residente", geography="brasil:1", dimensions=["c2"])
    assert len(one.series) == 3  # Total, Homens e Mulheres
    # A tabela devolve o diagnóstico V4, sem executar o cruzamento recusado.
    with monkeypatch.context() as guarded:

        def reject_query(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("Cruzamento inválido não pode consultar observações")

        guarded.setattr(stack["gold"], "run_plan", reject_query)
        pivot = service.pivot(
            ctx,
            "populacao_residente",
            level="uf",
            within=None,
            rows=["territorio"],
            cols=["c86", "c2"],
        )
        assert pivot.cells == []
        assert [a.code for a in pivot.alerts] == ["V4"]
    with pytest.raises(SemanticError, match="não tem o período"):
        service.pivot(
            ctx,
            "populacao_residente",
            level="uf",
            within=None,
            rows=["territorio"],
            cols=["periodo"],
            periods=["2999"],
        )
    # As fixtures da 9606 só têm o Total de idade: os grupos quinquenais não aparecem.
    detail = service.detail(
        ctx, "populacao_residente", geography="brasil:1", period="2022", dimensions=["c287"]
    )
    assert detail.root.children == []
    assert detail.root.value is not None


def test_source_tables_and_dimension_coverage(stack: dict[str, Any]) -> None:
    """DS 2.9: cada detalhe diz de que tabela vem; o KPI lista as tabelas de origem."""
    kpi = _get(stack, "/api/v1/kpis/populacao_residente")
    tables = kpi["source"]["tables"]
    assert tables, "o KPI publicado tem ao menos a tabela principal"
    assert tables[0]["table_id"] == kpi["source"]["source_table_id"]  # a principal primeiro
    assert tables[0]["periods"] == sorted(tables[0]["periods"])
    by_id = {d["classification_id"]: d for d in kpi["dimensions"]}
    assert by_id["c2"]["source_table_ids"] == ["9606"]
    assert "c2" in tables[0]["classification_ids"]
    # Sem links configurados no teste: o da tabela principal vem do indicador.
    assert tables[0]["reference_url"] == kpi["source"]["reference_url"]


def test_dimension_levels_follow_release_coverage(stack: dict[str, Any]) -> None:
    """Detalhe sem categorias num nível gravado: o nível sai de ``levels`` (DS 2.9)."""
    service: KpiService = KpiService(
        stack["gold"], load_portal(PORTAL_DIR, "demografia"), page_max=100
    )
    ctx = ReleaseContext(stack["state"]["release"])
    real = stack["gold"].coverage(ctx)

    class Partial:
        """Gold cujo detalhe por sexo só existe nas UFs."""

        def __getattr__(self, name: str) -> Any:
            return getattr(stack["gold"], name)

        def coverage(self, _ctx: Any) -> Any:
            cov = {k: dict(v) for k, v in real.items()}
            ind = service.kpi(ctx, "populacao_residente").indicator
            cov[ind] = {
                t: {**v, "classifications": {**v["classifications"], "c2": {"uf"}}}
                for t, v in real[ind].items()
            }
            return cov

    service._gold = Partial()  # type: ignore[assignment]
    kpi = service.kpi(ctx, "populacao_residente")
    meta = stack["gold"].indicators(ctx)[kpi.indicator]
    dims = {d.classification_id: d for d in service.describe(ctx, kpi, "t", "s").dimensions}
    stored = set().union(*(t["levels"] for t in real[kpi.indicator].values()))
    assert set(dims["c2"].levels) == {"uf"} | (set(meta["available_levels"]) - stored)
    assert dims["c86"].levels == []  # coberto em todos os níveis gravados


def test_table_links_from_source_configuration() -> None:
    """Link oficial de cada tabela: o ``reference_url`` configurado, nunca montado."""
    from odb_api.deps import table_links  # noqa: PLC0415
    from odb_ingestion.config import load_sources  # noqa: PLC0415

    links = table_links(load_sources(REPO / "configs" / "sources"))
    assert links["4490"] == "https://sidra.ibge.gov.br/tabela/4490"
    assert links["4487"] == "https://sidra.ibge.gov.br/tabela/4487"


def test_pivot_follows_periods_and_has_footer(stack: dict[str, Any]) -> None:
    """DS 2.9: a dinâmica segue os períodos do portal e traz a linha de totais."""
    base = "/api/v1/kpis/populacao_residente/pivot?level=uf&rows=territorio&cols=periodo"
    every = _get(stack, base)
    assert [c["labels"] for c in every["columns"]] == [["2010"], ["2022"]]
    one = _get(stack, base + "&periods=2022")
    assert [c["labels"] for c in one["columns"]] == [["2022"]]
    assert one["footer"]["keys"] == ["brasil:1"]
    assert one["footer_cells"][0]["value"] == 203080756
    within = _get(stack, base + "&periods=2022&within=regiao:2")
    assert within["footer"]["keys"] == ["regiao:2"]
    # Dimensão nas linhas: sem linha de totais (o % por coluna não se aplica).
    by_sex = _get(
        stack,
        "/api/v1/kpis/populacao_residente/pivot?level=uf&rows=territorio,c2&cols=periodo&periods=2022",
    )
    assert by_sex["footer"] is None
