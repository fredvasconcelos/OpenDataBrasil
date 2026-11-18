"""Datasets que pedem a mesma tabela SIDRA em recortes disjuntos (um KPI por categoria)."""

from __future__ import annotations

from pathlib import Path

import pytest

from odb_ingestion.config import ConfigError, load_sources
from odb_ingestion.connectors.sidra import SidraConnector, SidraParams, shared_table_partition


def _params(variables: list[str], classifications: dict[str, str], **extra: object) -> SidraParams:
    return SidraParams.model_validate(
        {
            "table": "74",
            "variables": variables,
            "territorial_levels": ["n1"],
            "estimated_values_per_period": 1,
            "classifications": classifications,
            **extra,
        }
    )


def test_category_sets_exclude_varying_classifications() -> None:
    params = _params(["106"], {"c80": "2687", "c2": "4,5"})
    assert params.category_sets() == {"c80": {"2687"}, "c2": {"4", "5"}}
    detailed = _params(
        ["106"],
        {"c80": "2687", "c2": "6794"},
        detail_classification="c2",
        detail_total="6794",
        detail_levels=["n1"],
    )
    assert detailed.category_sets() == {"c80": {"2687"}}
    assert _params(["106"], {"c80": "all"}).category_sets() == {}


def test_disjoint_category_sets_share_a_table() -> None:
    leite = _params(["106"], {"c80": "2682"})
    ovos = _params(["106"], {"c80": "2685,2686"})
    kg = _params(["106"], {"c80": "2687,2684,2683"})
    assert shared_table_partition("ovos", ovos, {"leite": leite, "kg": kg}) == (
        "classification_key",
    )


def test_no_siblings_keeps_table_partition() -> None:
    assert shared_table_partition("a", _params(["106"], {"c80": "2687"}), {}) == ()


def test_category_per_dataset_partitions_by_classification_key() -> None:
    mel = _params(["106"], {"c80": "2687"})
    la = _params(["106"], {"c80": "2684"})
    assert shared_table_partition("mel", mel, {"la": la}) == ("classification_key",)


def test_variable_and_category_both_separate() -> None:
    valor = _params(["215"], {"c654": "0,79366,32887"})
    peixes = _params(["4146"], {"c654": "79366"})
    camarao = _params(["4146"], {"c654": "32887"})
    assert shared_table_partition("valor", valor, {"peixes": peixes, "camarao": camarao}) == (
        "variable_id",
    )
    assert shared_table_partition("peixes", peixes, {"valor": valor, "camarao": camarao}) == (
        "variable_id",
        "classification_key",
    )


def test_overlapping_datasets_are_rejected() -> None:
    total = _params(["106"], {"c80": "2682,2687"})  # o mel está nos dois
    mel = _params(["106"], {"c80": "2687"})
    with pytest.raises(ConfigError, match="se sobrepõem"):
        shared_table_partition("mel", mel, {"total": total})


def test_catalogo_separa_instrucao_das_capitais_do_detalhe_por_raca() -> None:
    """A carga municipal da 7270 não pode substituir as linhas usadas pela série 7189."""
    sources = load_sources(Path(__file__).parents[3] / "configs" / "sources")
    capitals = sources.dataset("ibge-sidra-7270-capitais")
    params = SidraConnector.params(capitals)
    siblings = SidraConnector.siblings(sources, capitals)
    assert set(siblings) == {"ibge-sidra-7270"}
    assert params.category_sets()["c86"] == {"95251"}
    assert not params.category_sets()["c86"] & siblings["ibge-sidra-7270"].category_sets()["c86"]
    assert shared_table_partition(capitals.id, params, siblings) == ("classification_key",)
    assert shared_table_partition(
        "ibge-sidra-7270", siblings["ibge-sidra-7270"], {capitals.id: params}
    ) == ("classification_key",)


def test_informalidade_trimestral_preserva_forca_de_trabalho_na_4093() -> None:
    """A nova medida municipal ocupa outra partição da mesma tabela Silver."""
    sources = load_sources(Path(__file__).parents[3] / "configs" / "sources")
    dataset = sources.dataset("ibge-sidra-4093-informalidade")
    params = SidraConnector.params(dataset)
    siblings = SidraConnector.siblings(sources, dataset)
    assert params.variables == ("12466",)
    assert params.period_start == "201504"
    assert all("12466" not in sibling.variables for sibling in siblings.values())
    assert shared_table_partition(dataset.id, params, siblings) == ("variable_id",)
