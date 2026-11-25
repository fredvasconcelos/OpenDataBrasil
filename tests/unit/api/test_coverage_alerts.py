"""Cobertura parcial, ausência, sigilo e referências históricas (ADR-0040)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from odb_api.coverage_alerts import CoverageCell, coverage_alerts, historical_expected
from odb_api.schemas import DimensionOut


def cell(
    territory: str = "municipio:1",
    *,
    period: str = "2008",
    category: str = "c1:0",
    status: str = "valid",
    has_value: bool = True,
) -> CoverageCell:
    """Célula pequena que preserva o status e a presença territorial."""
    return CoverageCell(territory, period, (category,), status, has_value, "1594")


def classify(**changes: Any) -> list[Any]:
    """Recorte completo por padrão; cada caso troca só o que precisa demonstrar."""
    args: dict[str, Any] = dict(
        level="municipio",
        periods=["2008"],
        level_periods=["2008"],
        dimensions=[],
        active=[],
        detail_periods={},
        cells=[cell()],
        expected={},
    )
    args.update(changes)
    return coverage_alerts(**args)


def dimension(**changes: Any) -> DimensionOut:
    """Dimensão com o Total oficial e as categorias publicadas pela fixture."""
    args: dict[str, Any] = dict(
        classification_id="c1",
        label="Situação",
        full_label="Situação",
        partition_id="todas",
        total_category_key="c1:0",
        categories=[],
        source_table_ids=["1594"],
    )
    args.update(changes)
    return DimensionOut(**args)


def test_pof_serie_menor_e_subconjunto_historico() -> None:
    """26 municípios de 2008: não trocar o universo pelo cadastro atual."""
    alerts = classify(
        periods=["2002", "2008", "2018"],
        cells=[cell(f"municipio:{i}") for i in range(26)],
        expected={("1594", "2008"): (5564, "sidra:t1594:visao:10")},
    )
    assert [(a.code, a.severity) for a in alerts] == [("A1", "warning"), ("A2", "warning")]
    assert alerts[1].params.observed == 26
    assert alerts[1].params.expected == 5564
    assert alerts[0].params.available_periods == ["2008"]


@pytest.mark.parametrize(
    ("status", "has_value"),
    [("true_zero", True), ("suppressed", False), ("incomplete_period", False)],
)
def test_zero_sigilo_e_periodo_incompleto_nao_sao_ausencia(status: str, has_value: bool) -> None:
    """C10 não muda de classe por proporção de sigilo ou por valor zero."""
    assert (
        classify(
            cells=[cell(status=status, has_value=has_value)],
            expected={("1594", "2008"): (1, "referencia")},
        )
        == []
    )


def test_detalhe_ausente_e_precedencia_vermelha() -> None:
    """Um detalhe indisponível é V1 mesmo quando a série menor também é A1."""
    alerts = classify(
        periods=["2008", "2018"], dimensions=[dimension(levels=["uf"])], active=["c1"]
    )
    assert [a.code for a in alerts] == ["V1", "A1"]
    assert alerts[0].params.available_levels == ["uf"]


def test_so_total_e_detalhe_temporal_parcial() -> None:
    """V2 descreve o recorte; A3 mantém a informação sobre os outros períodos."""
    alerts = classify(
        dimensions=[dimension()],
        active=["c1"],
        periods=["2008", "2018"],
        level_periods=["2008", "2018"],
        detail_periods={"c1": ["2018"]},
        selected_periods=["2008"],
    )
    assert [a.code for a in alerts] == ["V2", "A3"]


def test_categoria_parcial_compara_o_total_do_mesmo_periodo() -> None:
    """C5 usa presença, incluindo sigilo; nenhum valor é completado ou somado."""
    alerts = classify(
        dimensions=[dimension()],
        active=["c1"],
        cells=[
            cell("municipio:1"),
            cell("municipio:2"),
            cell("municipio:1", category="c1:1", status="suppressed", has_value=False),
        ],
    )
    assert [a.code for a in alerts] == ["A3"]
    assert alerts[0].params.reference == "published_total"
    assert (alerts[0].params.observed, alerts[0].params.expected) == (1, 2)


@pytest.mark.parametrize("cells", [[], [cell(status="not_available", has_value=False)]])
def test_sem_linhas_ou_so_indisponivel_e_vermelho(cells: list[CoverageCell]) -> None:
    """Ausência de dado no período selecionado não é confundida com sigilo."""
    alerts = classify(cells=cells)
    assert [a.code for a in alerts] == ["V3"]
    assert alerts[0].params.periods == ["2008"]


def test_periodo_sem_dado_no_nivel_mantem_os_outros() -> None:
    """Um período vazio entre os escolhidos também recebe diagnóstico exato."""
    alerts = classify(periods=["2008", "2018"], selected_periods=["2008", "2018"])
    assert [a.code for a in alerts] == ["V3", "A1"]
    assert alerts[0].params.periods == ["2018"]


def test_regiao_parcial_e_cruzamento_recusado() -> None:
    """A4 conserva o valor parcial; V4 nunca fabrica células para marginais."""
    assert [a.code for a in classify(cells=[cell(status="partial_sum")])] == ["A4"]
    assert [a.code for a in classify(invalid_cross=True, active=["c1", "c2"])] == ["V4"]


def test_ordem_independe_da_ordem_das_celulas() -> None:
    """Diagnósticos estáveis não reabrem o botão por uma mudança de ordenação."""
    cells = [cell(period="2008"), cell(period="2018")]
    args = dict(
        expected={("1594", p): (2, "referencia") for p in ["2008", "2018"]},
        periods=["2008", "2018"],
        level_periods=["2008", "2018"],
    )
    assert classify(cells=cells, **args) == classify(cells=list(reversed(cells)), **args)


def test_descritor_so_aceita_universo_generico_com_intervalo_explicito(tmp_path: Path) -> None:
    """Visões de capitais, genéricas atuais e referências conflitantes não servem."""
    p = tmp_path / "t1594.json"
    views = [
        {
            "Id": 10,
            "Nome": "Município, em ordem de código de UF e código de Município - 2005-2008",
            "QuantidadeUnidades": 5564,
        },
        {"Id": 42, "Nome": "Município da Capital", "QuantidadeUnidades": 27},
    ]
    p.write_text(json.dumps({"VisoesTerritoriais": views}), encoding="utf-8")
    assert historical_expected(tmp_path, "1594", "municipio", "2008") == (
        5564,
        "sidra:t1594:visao:10",
    )
    assert historical_expected(tmp_path, "1594", "municipio", "2018") is None
    assert historical_expected(tmp_path, "../1594", "municipio", "2008") is None
    assert historical_expected(tmp_path, "1594", "uf", "2008") is None

    conflicting = [views[0], {**views[0], "Id": 11, "QuantidadeUnidades": 5563}]
    (tmp_path / "t1595.json").write_text(
        json.dumps({"VisoesTerritoriais": conflicting}), encoding="utf-8"
    )
    assert historical_expected(tmp_path, "1595", "municipio", "2008") is None
