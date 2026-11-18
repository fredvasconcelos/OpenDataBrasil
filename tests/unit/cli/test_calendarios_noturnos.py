"""Confere limites nativos de divulgação e ausência de totais inventados."""

from __future__ import annotations

from pathlib import Path

from odb_cli.panorama_agro import generate_agro
from odb_cli.panorama_medidas import generate_measures

CONFIGS = Path(__file__).parents[3] / "configs"


def test_lspa_preserva_culturas_retiradas_e_entrada_de_canola_e_gergelim() -> None:
    generated = generate_agro(CONFIGS)
    for dataset in generated.datasets:
        params = dataset["params"]
        if params["table"] != "6588":
            continue
        assert params["period_type"] == "mes"
        assert params["group_periods_by_year"]
        for category in params["classifications"]["c48"].split(","):
            if category in {
                "39447",
                "39448",
                "39458",
                "39459",
                "39461",
                "39464",
                "39465",
                "39468",
                "39469",
            }:
                assert params["periods"][-1] == "201712"
            if category in {"82223", "82224"}:
                assert params["periods"][0] == "202601"
            if category in {"39454", "39455"}:
                assert params["periods"][0] == "201201"
            if params["variables"][0] in {"35", "36"}:
                assert category != "0"
    hidden = {i["id"] for i in generated.indicators} - {k.id for _, _, k in generated.portal}
    assert {
        "safra_producao_ton",
        "safra_producao_frutos",
        "safra_rendimento_kg_ha",
        "safra_rendimento_frutos_ha",
    } <= hidden


def test_componentes_sinapi_respeitam_reais_e_indices_nao_herdam_agregacao() -> None:
    generated = generate_measures(CONFIGS)
    for dataset in generated.datasets:
        params = dataset["params"]
        if params["table"] == "2296" and params["variables"][0] in {"2119", "2120"}:
            assert params["periods"][0] == "201209"
            assert params["period_type"] == "mes"
    for _, _, kpi in generated.portal:
        if kpi.tabela in {"2296", "1736", "1737", "3065", "6904"}:
            assert kpi.correcao is None
            assert kpi.agregacao_tempo is None
