"""Confere integridade da auditoria, bloqueios da fonte e prova de cruzamentos."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

SCRIPT = Path(__file__).parents[3] / "infrastructure/scripts/revisao_detalhamento_kpis.py"
SPEC = importlib.util.spec_from_file_location("revisao_detalhamento", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def snapshot(*tables: str) -> dict[str, Any]:
    """Monta um catálogo mínimo sem consultar serviços externos."""
    return {
        "themes": [
            {
                "subthemes": [
                    {
                        "kpis": [
                            {
                                "source": {
                                    "system": "SIDRA",
                                    "tables": [{"table_id": t} for t in tables],
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.mark.parametrize("status", [403, 405, 429])
def test_bloqueio_interrompe_e_impede_retomada_automatica(tmp_path: Path, status: int) -> None:
    fetch = Mock(return_value=(status, b"bloqueado"))
    with patch.object(MODULE.time, "sleep"):
        index = MODULE.collect_descriptors(snapshot("2609", "2654"), tmp_path, fetch=fetch)
        with pytest.raises(ValueError, match="não retomar automaticamente"):
            MODULE.collect_descriptors(snapshot("2609", "2654"), tmp_path, fetch=fetch)
    assert fetch.call_count == 1
    assert list(index) == ["2609"]


def test_retomada_confere_hash_e_nao_repete_download_valido(tmp_path: Path) -> None:
    fetch = Mock(return_value=(200, b'{"Id":2609}'))
    with patch.object(MODULE.time, "sleep"):
        index = MODULE.collect_descriptors(snapshot("2609"), tmp_path, fetch=fetch)
        MODULE.collect_descriptors(snapshot("2609"), tmp_path, fetch=fetch)
        assert fetch.call_count == 1
        (tmp_path / index["2609"]["path"]).write_bytes(b"alterado")
        with pytest.raises(ValueError, match="mudou no disco"):
            MODULE.collect_descriptors(snapshot("2609"), tmp_path, fetch=fetch)
    assert fetch.call_count == 1


def test_http_200_com_identificacao_errada_nao_e_descritor_confirmado(tmp_path: Path) -> None:
    fetch = Mock(side_effect=[(200, b'{"Id":2654}'), (200, b'{"Id":2609}')])
    with patch.object(MODULE.time, "sleep"):
        first = MODULE.collect_descriptors(snapshot("2609"), tmp_path, fetch=fetch)
        assert "error" in first["2609"]
        assert MODULE._load_descriptors(tmp_path) == {}
        second = MODULE.collect_descriptors(snapshot("2609"), tmp_path, fetch=fetch)
    assert "error" not in second["2609"]
    assert first["2609"]["path"] != second["2609"]["path"]


def test_alias_de_outra_tabela_e_harmonizacao_nao_provam_equivalencia_nativa() -> None:
    assert MODULE.native_classification("c2t2609", "2609") == "2"
    assert MODULE.native_classification("c2t2609", "2654") is None
    assert MODULE.native_classification("c11558h", "9509") is None


def test_hierarquia_nao_trata_idades_simples_como_irmas_dos_grupos() -> None:
    categories = MODULE._native_categories(
        [
            {"Id": 0, "NivelIdentacao": 0},
            {"Id": 5414, "NivelIdentacao": 1},
            {"Id": 5371, "NivelIdentacao": 2},
            {"Id": 5372, "NivelIdentacao": 2},
            {"Id": 5415, "NivelIdentacao": 1},
        ]
    )
    assert categories["5371"]["parent_id"] == "5414"
    assert categories["5372"]["parent_id"] == "5414"
    assert categories["5415"]["parent_id"] == "0"


def test_marginais_e_cruzamento_com_eixo_extra_nao_provam_celulas_conjuntas() -> None:
    kpi = {
        "kpi_id": "nascidos_vivos",
        "exclusive_dimensions": True,
        "levels": ["brasil", "municipio"],
        "crossed_levels": ["brasil"],
        "crossed": [["c2t2609", "c240"]],
    }
    classes = [
        {"classification_id": "2", "api_dimensions": ["c2t2609"]},
        {"classification_id": "240", "api_dimensions": ["c240"]},
    ]
    patterns = [
        {"level_id": "brasil", "period": "2024", "dimensions": dims}
        for dims in [["c2t2609"], ["c240"], ["c2t2609", "c240", "c232"]]
    ]
    args = (
        kpi,
        {"source_table_id": "2609", "source_variable_id": "217"},
        {"NiveisTerritoriais": [{"Id": 1, "Nome": "Brasil"}]},
        classes,
        patterns,
    )
    row = MODULE._cross_rows(*args, level_ids={"1": "brasil"})[0]
    assert row["api_config_allows"]
    assert not row["gold_has_joint_observations"]
    patterns.append({"level_id": "brasil", "period": "2023", "dimensions": ["c240", "c2t2609"]})
    row = MODULE._cross_rows(*args, level_ids={"1": "brasil"})[0]
    assert row["gold_periods_with_joint_observations"] == ["2023"]


def test_release_divergente_impede_reutilizar_estatisticas_antigas(tmp_path: Path) -> None:
    output, coverage = tmp_path / "atual", tmp_path / "anterior"
    output.mkdir()
    coverage.mkdir()
    for path, payload in [
        (output / "indice-descritores.json", {}),
        (output / "gold-metadata.json", {"release_id": "novo", "tables": {"dim": 2}}),
        (output / "gold-cruzamentos.json", {"release_id": "novo"}),
        (coverage / "catalogo-api.json", {"release_id": "novo", "tables": {"dim": 1}}),
    ]:
        path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="comparação misturada"):
        MODULE.compare_catalog({"release_id": "novo"}, output, coverage)


@pytest.mark.parametrize(("field", "value"), [("D2C", "999"), ("NC", "3"), ("D4C", "7")])
def test_http_200_nao_prova_recorte_com_coordenadas_diferentes(field: str, value: str) -> None:
    entry = {
        "table": "2609",
        "variables": ["217"],
        "level": "1",
        "period": "2024",
        "url": "https://apisidra.ibge.gov.br/values/t/2609/n1/all/v/217/p/2024/c2/0",
    }
    row = {"NC": "1", "D2C": "217", "D3C": "2024", "D4C": "0", field: value}
    with pytest.raises(ValueError, match="diverg"):
        MODULE.validate_probe(entry, [row])
