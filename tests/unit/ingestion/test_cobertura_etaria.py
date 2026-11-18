"""Confere a seleção etária aprovada e o orçamento de cada requisição oficial."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odb_ingestion import load_sources
from odb_ingestion.connectors.sidra import SidraParams

REPO = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("table", ["9954", "8176", "9765"])
def test_faixas_etarias_cabem_no_limite_em_todos_os_niveis(table: str) -> None:
    """Cada bloco usa categorias oficiais e fica abaixo de 50 mil valores."""
    source = load_sources(REPO / "configs/sources").dataset(f"ibge-sidra-{table}")
    params = SidraParams.model_validate(source.params)
    descriptor = json.loads((REPO / f"configs/catalog/descritores/t{table}.json").read_text())
    levels = {
        f"n{n['Id']}": n["QuantidadeUnidadesAtivas"] for n in descriptor["NiveisTerritoriais"]
    }
    classes = {
        f"c{c['Id']}": {str(x["Id"]) for x in c["Categorias"]} for c in descriptor["Classificacoes"]
    }
    groups = params.request_groups()
    municipal_ages: set[str] = set()
    for group in groups:
        selected = group.levels or params.territorial_levels
        rows = len(group.variables) * sum(levels[lv] for lv in selected)
        for cid, listed in group.classifications.items():
            categories = classes[cid] if listed == "all" else set(listed.split(","))
            assert categories <= classes[cid]
            rows *= len(categories)
        assert rows <= 50000
        assert rows <= params.max_rows
        if "n6" in selected:
            municipal_ages.update(group.classifications["c287"].split(","))
    assert len(municipal_ages) == 22  # Total e 21 faixas nativas, sem idades simples.
