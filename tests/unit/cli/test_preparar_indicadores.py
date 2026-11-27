"""Preparação estática das candidatas e contrato de projeção mensal."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from odb_cli.panorama import _generation
from odb_cli.panorama_gen import render_indicators
from odb_modeling.model import (
    DatasetInfo,
    _month_to_period,
    apply_table_transforms,
    build_observations,
    indicator_map,
    select_silver,
    strip_fixed_categories,
)
from odb_processing.parsers import Lineage, parse_sidra
from odb_semantics import Panorama, load_catalog, load_panorama

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "preparar_indicadores", ROOT / "infrastructure/scripts/preparar_indicadores.py"
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_cinquenta_candidatas_tem_configuracao_ficha_e_impedimentos_preservados() -> None:
    result = MODULE.prepare(ROOT)
    assert result["total"] == 50
    assert result["por_lote"] == {"N3": 21, "N4": 11, "N5": 18}
    for entry in result["indicadores"]:
        assert all(entry["checks"].values())
        assert entry["publicavel"] is False
        if entry["lote"] == "N5":
            assert "reprovada" in entry["situacao"]


def _monthly(crossed: bool) -> Panorama:
    data = load_panorama(ROOT / "configs/catalog/panorama.toml").model_dump()
    for theme in data["temas"]:
        for sub in theme["subtemas"]:
            for kpi in sub["kpis"]:
                if kpi["id"] == "obitos":
                    kpi["mes_detalhes"] = ["c2"]
                    if crossed:
                        kpi["cruzar"] = [*kpi["cruzar"], ["c244", "c2"]]
    return Panorama.model_validate(data)


def test_projecao_mensal_preserva_sexo_e_exige_captura_conjunta() -> None:
    with pytest.raises(ValueError, match="captura conjunta"):
        _generation(
            _monthly(False), ROOT / "configs/catalog/panorama.toml", ROOT / "configs", "demografia"
        )
    gen = _generation(
        _monthly(True), ROOT / "configs/catalog/panorama.toml", ROOT / "configs", "demografia"
    )
    fact = next(f for f in gen.facts if f["id"] == "fact_sidra_2654_mensal")
    assert fact["classifications"] == {"c2t2654": "c2t2654_category_key"}
    assert "Sexo" not in fact["table_rules"]["2654"]["fixed_categories"]
    source = next(d for d in gen.datasets if d["official_id"] == "2654")
    assert any({"c244", "c2"} <= set(group) for group in source["params"]["cross_sets"])
    assert gen.dimensions["obitos_mensal"]["classification"] == "c2t2654"


def test_piloto_oficial_2654_conserva_as_48_celulas_mes_sexo(tmp_path: Path) -> None:
    path = ROOT / "tests/fixtures/ibge/sidra/t2654_n1_p2024_v343_c244_c2.json"
    content = path.read_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    assert checksum == "53973f8c1601c5f0a0f81f80493064450b00cbd51e920eadceab49d0739683c6"
    now = datetime(2026, 11, 25, 15, 16, 19, tzinfo=UTC)
    lineage = Lineage(
        "piloto-2654", checksum, "https://apisidra.ibge.gov.br", now, "teste", "teste", now
    )
    silver = parse_sidra(content, table_id="2654", lineage=lineage)
    assert silver.height == 56
    monthly = _month_to_period(silver, "Mês de ocorrência")
    assert monthly.height == 48
    assert monthly["period"].n_unique() == 12
    sexes = monthly.select(
        pl.col("classifications")
        .list.eval(pl.element().filter(pl.element().struct.field("dimension") == "Sexo"))
        .list.first()
        .struct.field("category_id")
        .alias("sexo")
    )
    assert sexes["sexo"].n_unique() == 4
    assert not monthly["value"].is_null().any()
    # Conferência por valor bruto: a projeção apenas muda calendário/chave, não a medida.
    original_values = sorted(
        str(row["V"])
        for row in json.loads(content)[1:]
        if str(row.get("D4C")) not in {"0", "102885"}
    )
    assert sorted(monthly["value_raw"].to_list()) == original_values
    gen = _generation(
        _monthly(True), ROOT / "configs/catalog/panorama.toml", ROOT / "configs", "demografia"
    )
    candidate = tmp_path / "panorama.toml"
    candidate.write_text(render_indicators(gen, "demografia"))
    fragments = [
        p
        for p in sorted((ROOT / "configs/indicators/demografia").glob("*.toml"))
        if p.name != "panorama.toml"
    ]
    catalog = load_catalog(ROOT / "configs/indicators/demografia.toml", [*fragments, candidate])
    catalog = catalog.model_copy(
        update={
            "facts": tuple(f for f in catalog.facts if f.id == "fact_sidra_2654_mensal"),
            "indicators": tuple(i for i in catalog.indicators if i.id == "obitos_mensal"),
        }
    )
    mapping = indicator_map(
        catalog,
        {
            "ibge-sidra-2654": DatasetInfo(
                "ibge-sidra-2654",
                "2654",
                "https://sidra.ibge.gov.br/tabela/2654",
                "ibge-reuso-com-citacao",
            )
        },
    )
    selected = apply_table_transforms(select_silver(silver, mapping, catalog), catalog)
    selected, _ = strip_fixed_categories(selected, catalog)
    gold = build_observations(
        selected, catalog, silver_version=0, build_id="teste-piloto", pending={}
    )
    assert gold.height == 48
    assert gold["breakdown_key"].n_unique() == 4
    assert gold["period"].n_unique() == 12
    assert sorted(gold["value"].to_list()) == sorted(monthly["value"].to_list())
