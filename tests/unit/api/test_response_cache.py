"""Cache de respostas por release (plano R-V, V5)."""

from __future__ import annotations

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from odb_api.response_cache import CACHEABLE, ResponseCache, make_cache_middleware


def _app(cache: ResponseCache, state: dict[str, object]) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(make_cache_middleware(cache, lambda: str(state["release"])))

    @app.get("/api/v1/kpis/{kpi_id}/map")
    @app.get("/api/v1/kpis/{kpi_id}/pivot")
    def mapa(kpi_id: str, level: str = "uf") -> Response:
        state["calls"] = int(str(state["calls"])) + 1
        status = 422 if level == "ruim" else 200
        body = f'{{"kpi":"{kpi_id}","level":"{level}","r":"{state["release"]}"}}'
        return Response(
            body, status_code=status, media_type="application/json",
            headers={"X-ODB-Release": str(state["release"])},
        )  # fmt: skip

    @app.get("/api/v1/release")
    def release() -> dict[str, object]:
        state["calls"] = int(str(state["calls"])) + 1
        return {"release_id": state["release"]}

    return app


def test_hit_miss_and_release_change() -> None:
    state: dict[str, object] = {"release": "r1", "calls": 0}
    client = TestClient(_app(ResponseCache(1024 * 1024), state))
    first = client.get("/api/v1/kpis/pop/map?level=uf")
    assert first.headers["x-odb-cache"] == "miss"
    second = client.get("/api/v1/kpis/pop/map?level=uf")
    assert second.headers["x-odb-cache"] == "hit"
    assert second.content == first.content
    assert second.headers["x-odb-release"] == "r1"
    assert state.get("calls") == 1
    # Outra URL (outra consulta) não reaproveita.
    client.get("/api/v1/kpis/pop/map?level=municipio")
    assert state.get("calls") == 2
    # Troca de release (ou rollback): a chave muda, nada do release anterior é servido.
    state["release"] = "r2"
    third = client.get("/api/v1/kpis/pop/map?level=uf")
    assert third.headers["x-odb-cache"] == "miss"
    assert b'"r":"r2"' in third.content
    assert state.get("calls") == 3


def test_only_cacheable_get_200() -> None:
    state: dict[str, object] = {"release": "r1", "calls": 0}
    client = TestClient(_app(ResponseCache(1024 * 1024), state))
    for _ in range(2):
        assert "x-odb-cache" not in client.get("/api/v1/release").headers  # fora da lista
        assert client.get("/api/v1/kpis/pop/map?level=ruim").status_code == 422  # erro
    assert state.get("calls") == 4


def test_cacheable_routes() -> None:
    # Teste de carga de 2026-11-17: a tabela dinâmica (36% do tempo da API) e a série
    # completa ficavam fora do cache e eram recalculadas em toda visita.
    for route in ("map", "series", "detail", "table", "pivot", "history"):
        assert CACHEABLE.match(f"/api/v1/kpis/populacao_estimada/{route}")
    assert CACHEABLE.match("/api/v1/geographies/uf:35")
    for other in ("/api/v1/exports", "/api/v1/release", "/api/v1/kpis/pop/map/x"):
        assert not CACHEABLE.match(other)


def test_disabled_and_size_bound() -> None:
    state: dict[str, object] = {"release": "r1", "calls": 0}
    off = TestClient(_app(ResponseCache(0), state))
    off.get("/api/v1/kpis/pop/map")
    off.get("/api/v1/kpis/pop/map")
    assert state.get("calls") == 2
    cache = ResponseCache(400)  # cabe ~6 respostas pequenas; uma acima de 100 B nem entra
    for i in range(20):
        cache.put(("r1", f"/p{i}", ""), b"x" * 60, {})
    assert cache._size <= 400  # teto respeitado
    assert cache.get(("r1", "/p0", "")) is None  # descartada (a menos usada)
    assert cache.get(("r1", "/p19", "")) is not None
    cache.put(("r1", "/grande", ""), b"x" * 101, {})
    assert cache.get(("r1", "/grande", "")) is None


def test_cache_de_recusa_do_pivot_preserva_status_e_release() -> None:
    state: dict[str, object] = {"release": "r1", "calls": 0}
    client = TestClient(_app(ResponseCache(1024 * 1024), state))
    path = "/api/v1/kpis/pop/pivot?level=ruim"
    first = client.get(path)
    second = client.get(path)
    assert first.status_code == second.status_code == 422
    assert second.content == first.content
    assert first.headers["x-odb-cache"] == "miss"
    assert second.headers["x-odb-cache"] == "hit"
    assert state["calls"] == 1
    state["release"] = "r2"
    third = client.get(path)
    assert third.status_code == 422
    assert third.headers["x-odb-cache"] == "miss"
    assert third.headers["x-odb-release"] == "r2"
    # .get: o mypy guarda o valor 1 do assert anterior para state["calls"].
    assert state.get("calls") == 2
