"""Comandos `odb panorama validar`, `verificar` e `documentar` (ADR-0010)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from odb_cli import panorama as panorama_cli
from odb_cli.main import app
from odb_cli.panorama import render_catalog
from odb_semantics import check_against_acervo, load_panorama

REPO = Path(__file__).resolve().parents[3]
PANORAMA = REPO / "configs" / "catalog" / "panorama.toml"
PORTAL = REPO / "configs" / "portal"


def test_validar_reports_counts() -> None:
    result = CliRunner().invoke(
        app, ["panorama", "validar", "--panorama", str(PANORAMA), "--portal-dir", str(PORTAL)]
    )
    assert result.exit_code == 0, result.output
    # 12 curados com `kpi`, a 9605 e a 6715 pelo id do item, 92 KPIs de Total gerados.
    assert "20 temas, 64 subtemas, 156 KPIs (149 publicados, 7 planejados)" in result.output


def test_render_catalog_flags_coverage() -> None:
    config = load_panorama(PANORAMA)
    titles = check_against_acervo(config, PANORAMA.parent / config.acervo)
    verification = {
        "updated_at": "2026-11-10T00:00:00+00:00",
        "tables": [
            {
                "table": "417",
                "status": "ok",
                "base_level": "n7",
                "variables": [{"id": "180"}],
                "period_label": "Ano",
                "periods": ["1987", "2008"],
                "periods_complete": True,
                "classifications": [],
                "levels": {"n1": None, "n2": None, "n3": None, "n7": 9, "n6": 2},
            },
            {"table": "6579", "status": "erro", "error": "timeout"},
        ],
    }
    doc = render_catalog(config, titles, verification)
    assert doc.count("\n## ") == 20
    row = next(line for line in doc.splitlines() if "[417]" in line)
    assert "Ano 1987\u20132008 (2)" in row
    assert "RM (9), Município (2)" in row
    assert "sem nível Brasil (base: RM)" in row
    assert "último período 2008" in row
    assert "não verificada: timeout" in doc
    assert "não verificada" in doc
    assert "1 de 149 tabelas verificadas" in doc  # POF de 1987 e 1995 (387, 400, 414)


def test_verificar_writes_resumable_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    header = {
        "NC": "",
        "NN": "",
        "MC": "",
        "MN": "",
        "V": "",
        "D1C": "Brasil (Código)",
        "D1N": "Brasil",
        "D2C": "Variável (Código)",
        "D2N": "Variável",
        "D3C": "Ano (Código)",
        "D3N": "Ano",
    }
    row = {
        **header,
        "MN": "Pessoas",
        "V": "10",
        "D1C": "1",
        "D2C": "93",
        "D2N": "Pop",
        "D3C": "2022",
    }
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.raw_path.decode())
        if "/n1/" in request.url.raw_path.decode():
            return httpx.Response(200, content=json.dumps([header, row]).encode())
        return httpx.Response(
            400, text="Parâmetro N2 (Nível territorial) incompatível com a tabela"
        )

    monkeypatch.setattr(panorama_cli, "HTTP_TRANSPORT", httpx.MockTransport(handler))
    # Mesma fonte, sem o intervalo de 2 s entre requisições.
    sources = tmp_path / "sources"
    sources.mkdir()
    ibge = (REPO / "configs" / "sources" / "ibge.toml").read_text(encoding="utf-8")
    (sources / "ibge.toml").write_text(
        ibge.replace("min_interval_s = 2.0", "min_interval_s = 0.0"), encoding="utf-8"
    )
    monkeypatch.setenv("ODB_SOURCES_CONFIG_DIR", str(sources))
    out = tmp_path / "verificacao.json"
    args = ["panorama", "verificar", "--panorama", str(PANORAMA), "--saida", str(out)]
    result = CliRunner().invoke(app, [*args, "--tabela", "6579"])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [t["table"] for t in data["tables"]] == ["6579"]
    assert data["tables"][0]["levels"]["n1"] == 1
    assert data["acervo_sha256"] == load_panorama(PANORAMA).acervo_sha256
    # Retomar não consulta de novo as tabelas já verificadas.
    calls.clear()
    result = CliRunner().invoke(app, [*args, "--tabela", "6579", "--tabela", "4709", "--retomar"])
    assert result.exit_code == 0, result.output
    assert all("/t/4709/" in c for c in calls)
    assert [t["table"] for t in json.loads(out.read_text("utf-8"))["tables"]] == ["6579", "4709"]
    # Tabela fora do panorama: recusada sem consultar a fonte.
    result = CliRunner().invoke(app, [*args, "--tabela", "1"])
    assert result.exit_code == 2
