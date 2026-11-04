from pathlib import Path

import pytest

from odb_semantics import SemanticConfigError, load_catalog, load_scope
from tests.gold_support import REPO_INDICATORS

BASE = (REPO_INDICATORS / "demografia.toml").read_text(encoding="utf-8")


def _write(tmp_path: Path, content: str, name: str = "demografia.toml") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_repository_catalog_is_valid() -> None:
    catalog = load_scope(REPO_INDICATORS, "demografia")
    assert catalog.scope == "demografia"
    assert len(catalog.indicators) == 16
    assert catalog.datasets() == [
        "ibge-sidra-6579",
        "ibge-sidra-4714",
        "ibge-sidra-9605",
        "ibge-sidra-9718",
        "ibge-sidra-9578",
        "ibge-sidra-9971",
        "ibge-sidra-9970",
        "ibge-sidra-9723",
    ]
    c2661 = catalog.classification("c2661")
    assert c2661.partition_of("12869").id == "terras_indigenas"  # type: ignore[union-attr]
    assert c2661.partition_of("32776") is None
    assert c2661.declared() == {"32776", "12869", "12870", "60027", "60028"}
    assert not catalog.classification("c86").partitions[0].exhaustive
    assert [i.id for i in catalog.indicators_of("fact_census_population")] == [
        "censo_populacao_residente",
        "censo_area_territorial",
        "censo_densidade_demografica",
    ]
    pair = frozenset({"censo_pessoas_indigenas", "censo_populacao_cor_raca"})
    assert "população indígena" in catalog.incompatibilities()[pair]
    assert len(catalog.content_sha256) == 64


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            'fact = "fact_census_population"\ncolumn = "area_km2"',
            'fact = "fact_census_population"\ncolumn = "population"',
            "coluna population repetida",
        ),
        ('variable = "6318"', 'variable = "93"', "mais de um indicador"),
        (
            'fact = "fact_population_by_race"\ncolumn',
            'fact = "fact_inexistente"\ncolumn',
            "fato inexistente",
        ),
        (
            '{ indicator = "censo_populacao_cor_raca",',
            '{ indicator = "nao_existe",',
            "incompatibilidade inválida",
        ),
        (
            'classifications = { "c86" = "race_category_key" }',
            'classifications = { "c999" = "race_category_key" }',
            "não declaradas",
        ),
        ('categories = ["2776", "2777"', 'categories = ["95251", "2777"', "filho de si mesmo"),
        (
            'categories = ["60027", "60028"]',
            'categories = ["12869", "60028"]',
            "mais de uma partição",
        ),
        (
            'dataset = "ibge-sidra-9578"\nvariable = "4709"',
            'dataset = "ibge-sidra-9605"\nvariable = "4709"',
            "difere do fato",
        ),
    ],
)
def test_invalid_catalogs(tmp_path: Path, old: str, new: str, message: str) -> None:
    assert old in BASE, old
    with pytest.raises(SemanticConfigError, match=message):
        load_catalog(_write(tmp_path, BASE.replace(old, new, 1)))


def test_nested_partitions() -> None:
    catalog = load_scope(REPO_INDICATORS, "demografia")
    age = catalog.classification("c287")
    assert age.depth("100362") == 0
    assert age.depth("93070") == 1  # 0 a 4 anos
    assert age.depth("6557") == 2  # menos de 1 ano
    assert age.depth("93071") == 3  # menos de 1 mês
    order = age.ordered()
    assert len(order) == 134
    assert order[:4] == ["100362", "93070", "6557", "93071"]
    months = age.partition_of("93071")
    assert months is not None
    assert age.parent_of(months) == "6557"


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('parent = "6557"', 'parent = "99999"', "não declarado"),
        ('parent = "93070"', 'parent = "6558"', "ciclo"),
    ],
)
def test_invalid_nested_partitions(tmp_path: Path, old: str, new: str, message: str) -> None:
    assert old in BASE
    with pytest.raises(SemanticConfigError, match=message):
        load_catalog(_write(tmp_path, BASE.replace(old, new, 1)))


def test_scope_file_errors(tmp_path: Path) -> None:
    with pytest.raises(SemanticConfigError, match="não encontrado"):
        load_scope(tmp_path, "demografia")
    _write(tmp_path, BASE, "outro.toml")
    with pytest.raises(SemanticConfigError, match="difere do nome"):
        load_scope(tmp_path, "outro")
    _write(tmp_path, "isto não é toml = [", "quebrado.toml")
    with pytest.raises(SemanticConfigError, match="inválido"):
        load_catalog(tmp_path / "quebrado.toml")
