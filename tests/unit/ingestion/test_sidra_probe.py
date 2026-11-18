"""Sonda de metadados SIDRA (panorama, ADR-0010), com respostas simuladas."""

from __future__ import annotations

import json

import httpx

from odb_ingestion.config import HttpPolicy
from odb_ingestion.connectors.sidra_probe import probe_table
from odb_ingestion.http import HttpClient

BASE = "https://apisidra.ibge.gov.br"
HEADER = {
    "NC": "Nível Territorial (Código)",
    "NN": "Nível Territorial",
    "MC": "Unidade de Medida (Código)",
    "MN": "Unidade de Medida",
    "V": "Valor",
    "D1C": "Brasil (Código)",
    "D1N": "Brasil",
    "D2C": "Variável (Código)",
    "D2N": "Variável",
    "D3C": "Ano (Código)",
    "D3N": "Ano",
    "D4C": "Sexo (Código)",
    "D4N": "Sexo",
}


def _row(territory: str, var: str, unit: str, year: str) -> dict[str, str]:
    return {
        "NC": "1",
        "NN": "Brasil",
        "MC": "45",
        "MN": unit,
        "V": "1",
        "D1C": territory,
        "D1N": territory,
        "D2C": var,
        "D2N": f"Variável {var}",
        "D3C": year,
        "D3N": year,
        "D4C": "6794",
        "D4N": "Total",
    }


def _client(routes: dict[str, httpx.Response], seen: list[str]) -> HttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        seen.append(path)
        return routes.get(path) or httpx.Response(
            400, text="Parâmetro N9 (Nível territorial) incompatível com a tabela"
        )

    policy = HttpPolicy(min_interval_s=0.0, max_attempts=1)
    return HttpClient(policy, transport=httpx.MockTransport(handler))


def _territories(count: int) -> httpx.Response:
    return _ok([_row(str(i), "93", "Pessoas", "2022") for i in range(count)])


def _ok(rows: list[dict[str, str]]) -> httpx.Response:
    return httpx.Response(200, content=json.dumps([HEADER, *rows]).encode())


def test_probe_reads_variables_periods_totals_and_levels() -> None:
    t = "/values/t/9606"
    routes = {
        f"{t}/n1/all/v/all/p/all": _ok(
            [
                _row("1", "93", "Pessoas", "2010"),
                _row("1", "93", "Pessoas", "2022"),
                _row("1", "1000093", "Percentual", "2022"),
            ]
        ),
        f"{t}/n2/all/v/93/p/last%201": _territories(5),
        f"{t}/n3/all/v/93/p/last%201": _territories(27),
        f"{t}/n6/all/v/93/p/last%201": _territories(9),
    }
    seen: list[str] = []
    with _client(routes, seen) as http:
        probe = probe_table(http, BASE, "9606")
    assert probe.status == "ok"
    assert probe.base_level == "n1"
    assert [v["id"] for v in probe.variables] == ["93", "1000093"]
    assert probe.variables[1]["units"] == ["Percentual"]
    assert probe.period_label == "Ano"
    assert probe.periods == ["2010", "2022"]
    assert probe.classifications == [
        {"label": "Sexo", "categories": [{"id": "6794", "name": "Total"}]}
    ]
    assert probe.levels == {"n1": 1, "n2": 5, "n3": 27, "n7": None, "n6": 9}
    # O nível já descrito não é consultado de novo.
    assert seen.count(f"{t}/n1/all/v/93/p/last%201") == 0
    assert all(r.sha256 for r in probe.requests if r.status == 200)


def test_probe_falls_back_to_first_accepted_level_and_to_last_period() -> None:
    t = "/values/t/417"
    routes = {
        f"{t}/n7/all/v/all/p/all": httpx.Response(
            400, text="Quantidade de valores solicitados: 67236 excedeu o limite: 50000"
        ),
        f"{t}/n7/all/v/all/p/last%201": _ok([_row("2701", "180", "Quilogramas", "2008")]),
        f"{t}/n7/all/v/180/p/all": _ok(
            [_row("2701", "180", "Quilogramas", y) for y in ("1987", "2008")]
        ),
    }
    with _client(routes, []) as http:
        probe = probe_table(http, BASE, "417")
    assert probe.status == "ok"
    assert probe.base_level == "n7"
    assert probe.levels["n1"] is None
    assert probe.levels["n7"] == 1
    assert probe.periods == ["1987", "2008"]
    assert probe.periods_complete is False


def test_probe_reports_table_without_known_levels() -> None:
    with _client({}, []) as http:
        probe = probe_table(http, BASE, "1")
    assert probe.status == "erro"
    assert "nenhum dos níveis" in (probe.error or "")


def test_probe_reports_other_refusals() -> None:
    routes = {"/values/t/2/n1/all/v/all/p/all": httpx.Response(400, text="Tabela inexistente")}
    with _client(routes, []) as http:
        probe = probe_table(http, BASE, "2")
    assert probe.status == "erro"
    assert "Tabela inexistente" in (probe.error or "")
