"""Métricas de acesso na API (ADR-0027): período, supressão, cache e contrato das rotas."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from odb_api.app import create_app
from odb_api.config import ApiSettings
from odb_api.deps import ApiDeps
from odb_api.metrics import (
    MetricsQueryError,
    MetricsService,
    _Place,
    kpi_titles,
    resolve_period,
    suppress,
)
from odb_catalog.access_metrics import KpiCounts

TODAY = date(2026, 11, 17)


# ---------------------------------------------------------------------- período


@pytest.mark.parametrize(
    ("period", "start"),
    [("7d", date(2026, 11, 11)), ("30d", date(2026, 10, 19)), ("12m", date(2025, 11, 18))],
)
def test_shortcut_periods_end_today(period: Any, start: date) -> None:
    p = resolve_period(period, None, None, TODAY)
    assert (p.start, p.end) == (start, TODAY)


def test_twelve_months_from_leap_day() -> None:
    p = resolve_period("12m", None, None, date(2028, 2, 29))
    assert p.start == date(2027, 3, 1)


def test_custom_period() -> None:
    p = resolve_period("custom", date(2026, 1, 1), date(2026, 1, 31), TODAY)
    assert (p.start, p.end) == (date(2026, 1, 1), date(2026, 1, 31))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (None, date(2026, 1, 1)),
        (date(2026, 2, 1), date(2026, 1, 1)),
        (date(2025, 1, 1), date(2026, 1, 2)),  # 367 dias
        (date(2026, 11, 1), TODAY + timedelta(days=1)),
    ],
)
def test_invalid_custom_period(start: date | None, end: date | None) -> None:
    with pytest.raises(MetricsQueryError):
        resolve_period("custom", start, end, TODAY)


def test_dates_only_with_custom() -> None:
    with pytest.raises(MetricsQueryError):
        resolve_period("30d", date(2026, 1, 1), None, TODAY)


# -------------------------------------------------------------------- supressão


def test_primary_suppression_and_share_over_the_whole_cut() -> None:
    items = suppress(
        [_Place("a", "A", 90), _Place("b", "B", 3), _Place("c", "C", 7), _Place("d", "D", 0)]
    )
    by = {i.geography_key: i for i in items}
    assert (by["b"].status, by["b"].views, by["b"].share_pct) == ("suprimido", None, None)
    assert (by["d"].status, by["d"].views, by["d"].share_pct) == ("sem_acessos", 0, 0.0)
    # O total inclui o suprimido: 90 / 100.
    assert (by["a"].status, by["a"].views, by["a"].share_pct) == ("ok", 90, 90.0)


def test_no_complementary_suppression() -> None:
    # Decisão do mantenedor (2026-11-17): só a primária. A página diz "menos de 5" para
    # todo suprimido; a complementar exigiria outro rótulo (pendência na ADR-0027).
    items = suppress([_Place("a", "A", 90), _Place("b", "B", 3), _Place("c", "C", 7)])
    assert [i.status for i in items] == ["ok", "suprimido", "ok"]


def test_kpi_titles_from_navigation() -> None:
    nav = {
        "themes": [
            {"label": "População", "subthemes": [{"kpis": [{"kpi_id": "pop", "label": "Pop."}]}]}
        ]
    }
    assert kpi_titles(json.dumps(nav).encode()) == {"pop": ("Pop.", "População")}


# ------------------------------------------------------------------ serviço e rotas


@dataclass
class FakeReader:
    started: date | None = date(2026, 11, 17)
    calls: int = 0

    def collection_started(self) -> date | None:
        return self.started

    def totals(self, start: date, end: date) -> dict[str, int]:
        self.calls += 1
        return {"page_view": 120, "kpi_open": 30, "download": 4}

    def views_by_country(self, start: date, end: date) -> dict[str, int]:
        return {"BR": 100, "PT": 12, "AR": 2, "ZZ": 6}

    def views_by_uf(self, start: date, end: date) -> dict[int, int]:
        return {35: 60, 33: 20, 43: 9, 11: 3, 0: 8}

    def kpis(self, start: date, end: date) -> list[KpiCounts]:
        return [
            KpiCounts("pib", 12, 0),
            KpiCounts("populacao_estimada", 20, 3),
            KpiCounts("raro", 4, 9),
            KpiCounts("fora_do_release", 50, 50),
        ]


NAV = {
    "release_id": "r1",
    "themes": [
        {
            "label": "População e demografia",
            "subthemes": [
                {
                    "kpis": [
                        {"kpi_id": "populacao_estimada", "label": "População estimada"},
                        {"kpi_id": "raro", "label": "Raro"},
                    ]
                }
            ],
        },
        {"label": "Economia", "subthemes": [{"kpis": [{"kpi_id": "pib", "label": "PIB"}]}]},
    ],
}


class FakeResolver:
    def current(self) -> Any:
        return type("Ctx", (), {"release_id": "r1"})()


class FakeKpis:
    def serialized(self, ctx: Any) -> tuple[bytes, dict[str, bytes]]:
        return json.dumps(NAV).encode(), {}


def _client(reader: FakeReader | None) -> TestClient:
    deps = ApiDeps(
        settings=ApiSettings(rate_limit_per_minute=0),
        resolver=FakeResolver(),  # type: ignore[arg-type]
        gold=None,  # type: ignore[arg-type]
        kpis=FakeKpis(),  # type: ignore[arg-type]
        catalog=None,  # type: ignore[arg-type]
        engine=None,  # type: ignore[arg-type]
        metrics=MetricsService(reader, today=lambda: TODAY) if reader else None,  # type: ignore[arg-type]
    )
    return TestClient(create_app(deps))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with _client(FakeReader()) as c:
        yield c


def _ok(client: TestClient, path: str) -> Any:
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "public, max-age=300"
    return response.json()


@pytest.mark.parametrize("reader", [None, FakeReader(started=None)])
def test_no_collection_is_404(reader: FakeReader | None) -> None:
    # Sem banco configurado ou sem nenhuma contagem: a página diz que a coleta não começou.
    with _client(reader) as c:
        for path in ("summary", "geo?level=pais", "datasets"):
            response = c.get(f"/api/v1/metrics/{path}")
            assert response.status_code == 404, path
            assert response.json()["error"]["code"] == "not_found"


def test_summary(client: TestClient) -> None:
    body = _ok(client, "/api/v1/metrics/summary?period=7d")
    assert body["period"] == {"from": "2026-11-11", "to": "2026-11-17"}
    assert body["collection_started_at"] == "2026-11-17T00:00:00-03:00"
    assert (body["views"], body["kpi_opens"], body["downloads"]) == (120, 30, 4)
    # Países identificados (ZZ fora) e chamadas à API ainda não coletadas.
    assert body["countries"] == 3
    assert body["api_calls"] is None
    assert "unique_visitors" not in body


def test_summary_custom_period(client: TestClient) -> None:
    body = _ok(client, "/api/v1/metrics/summary?period=custom&from=2026-11-01&to=2026-11-10")
    assert body["period"] == {"from": "2026-11-01", "to": "2026-11-10"}
    response = client.get("/api/v1/metrics/summary?period=custom&from=2026-11-10&to=2026-11-01")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_geo_countries(client: TestClient) -> None:
    body = _ok(client, "/api/v1/metrics/geo?level=pais")
    by = {i["geography_key"]: i for i in body["items"]}
    assert by["pais:PT"]["name"] == "Portugal"
    assert by["pais:ZZ"]["name"] == "Não identificado"
    assert by["pais:AR"]["status"] == "suprimido"
    assert by["pais:AR"]["views"] is None
    assert (by["pais:ZZ"]["status"], by["pais:ZZ"]["views"]) == ("ok", 6)
    assert by["pais:BR"]["share_pct"] == 83.3


def test_geo_regions_include_zero_and_unknown(client: TestClient) -> None:
    body = _ok(client, "/api/v1/metrics/geo?level=regiao&within=pais:BR")
    by = {i["geography_key"]: (i["views"], i["status"]) for i in body["items"]}
    assert by == {
        "regiao:1": (None, "suprimido"),
        "regiao:2": (0, "sem_acessos"),
        "regiao:3": (80, "ok"),
        "regiao:4": (9, "ok"),
        "regiao:5": (0, "sem_acessos"),
        "regiao:0": (8, "ok"),  # Brasil sem UF identificada
    }


def test_geo_ufs(client: TestClient) -> None:
    body = _ok(client, "/api/v1/metrics/geo?level=uf&within=pais:BR")
    keys = [i["geography_key"] for i in body["items"]]
    assert len(keys) == 28  # 27 UFs (com zero, para o mapa) + a não identificada
    by = {i["geography_key"]: i for i in body["items"]}
    assert by["uf:35"]["name"] == "São Paulo"
    assert by["uf:0"]["name"] == "Estado não identificado"
    assert by["uf:11"]["status"] == "suprimido"
    body = _ok(client, "/api/v1/metrics/geo?level=uf&within=regiao:3")
    assert {i["geography_key"] for i in body["items"]} == {"uf:31", "uf:32", "uf:33", "uf:35"}


@pytest.mark.parametrize(
    "query",
    ["level=regiao", "level=uf", "level=pais&within=pais:BR", "level=uf&within=regiao:9"],
)
def test_geo_invalid_cut(client: TestClient, query: str) -> None:
    response = client.get(f"/api/v1/metrics/geo?{query}")
    assert response.status_code == 422, response.text


def test_datasets_ranking(client: TestClient) -> None:
    body = _ok(client, "/api/v1/metrics/datasets?sort=views")
    # "raro" tem menos de 5 aberturas; "fora_do_release" não está no release ativo.
    assert [(i["kpi_id"], i["title"], i["theme"], i["views"]) for i in body["items"]] == [
        ("populacao_estimada", "População estimada", "População e demografia", 20),
        ("pib", "PIB", "Economia", 12),
    ]
    body = _ok(client, "/api/v1/metrics/datasets?sort=downloads&limit=5")
    assert [i["kpi_id"] for i in body["items"]] == ["populacao_estimada"]
    assert client.get("/api/v1/metrics/datasets?limit=51").status_code == 422


def test_service_cache_lasts_five_minutes() -> None:
    reader = FakeReader()
    now = [0.0]
    service = MetricsService(reader, clock=lambda: now[0], today=lambda: TODAY)  # type: ignore[arg-type]
    period = resolve_period("30d", None, None, TODAY)
    service.summary(period)
    service.summary(period)
    assert reader.calls == 1
    now[0] = 301.0
    service.summary(period)
    assert reader.calls == 2


def test_acumulado_desde_a_coleta_supera_um_ano() -> None:
    with _client(FakeReader(started=date(2020, 1, 1))) as client:
        for path in ("summary", "geo?level=pais", "geo?level=uf&within=pais:BR", "datasets"):
            separator = "&" if "?" in path else "?"
            body = _ok(client, f"/api/v1/metrics/{path}{separator}period=all")
            assert body["period"] == {"from": "2020-01-01", "to": TODAY.isoformat()}
        assert client.get("/api/v1/metrics/summary?period=all&from=2020-01-01").status_code == 422


def test_acumulado_sem_coleta_permanece_indisponivel() -> None:
    with _client(FakeReader(started=None)) as client:
        assert client.get("/api/v1/metrics/summary?period=all").status_code == 404
