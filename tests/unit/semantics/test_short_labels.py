"""Rótulos curtos do portal (configs/portal/rotulos.toml, DS 2.3.11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from odb_semantics.portal import PortalConfigError, ShortLabels, load_short_labels

REPO = Path(__file__).resolve().parents[3]


def test_repository_labels_load_and_stay_short() -> None:
    labels = load_short_labels(REPO / "configs" / "portal" / "rotulos.toml")
    assert labels.dimension("c1821") == "Ligação à rede de água"
    assert labels.category("c1821:72144") == "Rede geral: forma principal"
    # Classificação própria de tabela (ADR-0014) usa o rótulo da origem.
    assert labels.dimension("c653t4423") == labels.dimension("c653")
    too_long = [v for v in (*labels.dimensoes.values(), *labels.categorias.values()) if len(v) > 40]
    assert not too_long


def test_category_keys_are_exact_and_missing_file_is_empty(tmp_path: Path) -> None:
    labels = ShortLabels(categorias={"c67t6736:4661": "Coleta direta"})
    assert labels.category("c67:4661") is None  # sem queda para a origem: códigos colidem
    assert load_short_labels(tmp_path / "nao-existe.toml") == ShortLabels()
    bad = tmp_path / "rotulos.toml"
    bad.write_text("[dimensoes]\nc1 = 3\n", encoding="utf-8")
    with pytest.raises(PortalConfigError):
        load_short_labels(bad)
