"""Confere cortes de moeda, unidades documentadas e coortes de produtos oficiais."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from odb_cli.panorama_agro import _cohorts, generate_agro
from odb_ingestion import load_sources
from odb_ingestion.connectors.sidra import SidraConnector, shared_table_partition

CONFIGS = Path(__file__).parents[3] / "configs"


def test_cortes_respeitam_reais_e_area_colhida_desde_1988() -> None:
    generated = generate_agro(CONFIGS)
    assert len(generated.indicators) == 12
    assert len(generated.portal) == 4
    for dataset in generated.datasets:
        p = dataset["params"]
        if p["variables"] == ["215"]:
            assert min(p["periods"]) >= "1994"
        if p["variables"] == ["216"]:
            assert min(p["periods"]) >= "1988"
        assert p["max_rows"] <= 50000
    spec = tomllib.loads((CONFIGS / "catalog/medidas-agro.toml").read_text())
    item = next(m for m in spec["measures"] if m["variable"] == "215")
    descriptor = json.loads((CONFIGS / "catalog/descritores/t5457.json").read_text())
    # Mesmo um corte configurado errado não permite baixar moedas anteriores.
    cohorts = _cohorts(descriptor, {**item, "first_period": "1993"}, {})
    assert all(min(periods) >= "1994" for periods in cohorts)


def test_produtos_e_periodos_nao_se_repetem_e_seguem_o_descritor() -> None:
    generated = generate_agro(CONFIGS)
    seen: set[tuple[str, str, str, str]] = set()
    for dataset in generated.datasets:
        p = dataset["params"]
        descriptor = json.loads((CONFIGS / f"catalog/descritores/t{p['table']}.json").read_text())
        categories = {str(c["Id"]): c for c in descriptor["Classificacoes"][0]["Categorias"]}
        codes = next(iter(p["classifications"].values())).split(",")
        for code in codes:
            assert code in categories
            for period in p["periods"]:
                key = (p["table"], p["variables"][0], code, period)
                assert key not in seen
                seen.add(key)
                if p["variables"][0] in ("214", "112"):
                    assert code != "0"
                    if code == "40136":
                        assert period >= "2001"
                    if code == "40139":
                        assert period >= "2002"
                if code == "83388":  # abóbora só entrou na PAM em 2025
                    assert period == "2025"


def test_coortes_e_variaveis_nao_substituem_recortes_anteriores() -> None:
    catalog = load_sources(CONFIGS / "sources")
    for dataset in catalog.datasets.values():
        if "ibge-agro-" not in str(dataset.silver.get("series", "")):
            continue
        params = SidraConnector.params(dataset)
        columns = shared_table_partition(
            dataset.id, params, SidraConnector.siblings(catalog, dataset)
        )
        assert "variable_id" in columns
        for group in params.request_groups():
            codes = next(iter(group.classifications.values())).split(",")
            if "n6" in (group.levels or params.territorial_levels):
                assert len(codes) <= 8
            else:
                descriptor = json.loads(
                    (CONFIGS / f"catalog/descritores/t{params.table}.json").read_text()
                )
                units = sum(
                    n["QuantidadeUnidadesAtivas"]
                    for n in descriptor["NiveisTerritoriais"]
                    if f"n{n['Id']}" in (group.levels or params.territorial_levels)
                )
                frequency = 12 if params.period_type == "mes" else 4
                assert units * len(codes) * frequency <= (params.max_rows or 0) <= 50000


def test_unidades_documentadas_nao_convertem_valores() -> None:
    generated = generate_agro(CONFIGS)
    overrides = [f for f in generated.facts if f.get("table_rules")]
    assert len(overrides) == 4
    assert {rule["unit"] for f in overrides for rule in f["table_rules"].values()} == {
        "Mil frutos",
        "Frutos por Hectare",
    }
    assert all(set(rule) == {"unit"} for f in overrides for rule in f["table_rules"].values())
