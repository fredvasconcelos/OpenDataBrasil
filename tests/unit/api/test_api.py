"""API sobre uma Gold construída com fixtures reais (e malhas sintéticas)."""

import dataclasses
import io
import json
import re
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from odb_api.app import create_app
from odb_api.config import ApiSettings
from odb_api.deps import ApiDeps
from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService
from odb_api.middleware import RateLimiter
from odb_api.portal import PortalConfigError, check_against_release, load_portal
from odb_api.release import ReleaseContext, ReleaseResolver, ReleaseUnavailableError
from odb_catalog.publication import Release, TableVersion
from odb_query_engine import DuckDBConfig, DuckDBReadEngine
from odb_semantics import PanoramaConfigError, load_panorama
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
PANORAMA.write_text(
    re.sub(
        r"\nexternos = \[.*?\n\]\n", "\n", PANORAMA_REPO.read_text(encoding="utf-8"), flags=re.S
    ),
    encoding="utf-8",
)


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
    assert _get(stack, "/health") == {"status": "ok", "release_id": "rel-1"}
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
    assert (root["label"], root["value"], root["share_pct"]) == ("Total", 14141626, None)
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
    assert series["series"][0]["points"] == [
        {"period": "2010", "value": 190755799, "status": "valid"},
        {"period": "2022", "value": 203080756, "status": "valid"},
    ]

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


def test_non_additive_kpi_has_no_shares(stack: dict[str, Any]) -> None:
    detail = _get(stack, "/api/v1/kpis/percentual_indigenas/detail?geography=uf:13")
    assert detail["additivity"] == "non_additive"
    assert detail["root"]["share_pct"] is None
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


def test_exports_carry_metadata(stack: dict[str, Any]) -> None:
    client = stack["client"]
    payload = {"kpi_id": "populacao_residente", "level": "uf", "dimensions": ["c86", "c2"]}
    csv = client.post("/api/v1/exports", json=payload | {"format": "csv"})
    assert csv.status_code == 200, csv.text
    assert 'filename="populacao_residente_uf.zip"' in csv.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(csv.content)) as archive:
        rows = archive.read("dados.csv").decode("utf-8-sig").splitlines()
        meta = json.loads(archive.read("metadados.json"))
    assert rows[0] == "geography_key,territorio,uf,periodo,Cor ou raça,Sexo,valor,status,unidade"
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


def test_portal_config_is_checked(tmp_path: Path, stack: dict[str, Any]) -> None:
    text = (PORTAL_DIR / "demografia.toml").read_text(encoding="utf-8")
    bad_order = text.replace('dimension_order = ["c86", "c2",', 'dimension_order = ["c2", "c86",')
    (tmp_path / "demografia.toml").write_text(bad_order, encoding="utf-8")
    with pytest.raises(PortalConfigError, match="fora da ordem"):
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
