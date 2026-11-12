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
    catalog = load_catalog(REPO_INDICATORS / "demografia.toml")
    assert catalog.scope == "demografia"
    assert len(catalog.indicators) == 22
    assert len(catalog.consistency) == 6
    assert catalog.datasets() == [
        "ibge-sidra-6579",
        "ibge-sidra-4714",
        "ibge-sidra-9605",
        "ibge-sidra-9718",
        "ibge-sidra-9578",
        "ibge-sidra-9971",
        "ibge-sidra-9970",
        "ibge-sidra-9723",
        "ibge-sidra-9954",
        "ibge-sidra-9606",
        "ibge-sidra-8176",
        "ibge-sidra-9765",
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
            'reference = "censo_populacao_residente"',
            'reference = "censo_area_territorial"',
            "conceito ou unidade diferentes",
        ),
        (
            'reference = "censo_pessoas_quilombolas"',
            'reference = "nao_existe"',
            "consistência inválida",
        ),
        (
            'level = "regiao"\nderive_from = "uf"',
            'level = "regiao"\nderive_from = "brasil"',
            "precisa ser um nível com malha oficial",
        ),
        (
            'level = "brasil"\nderive_from = "uf"',
            'level = "brasil"\ndataset = "x"\nderive_from = "uf"',
            "informe dataset ou derive_from",
        ),
        ('level = "brasil"\nderive_from', 'level = "uf"\nderive_from', "geometria repetida"),
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


def test_scope_merges_fragments(tmp_path: Path) -> None:
    _write(tmp_path, BASE)
    (tmp_path / "demografia").mkdir()
    fragment = """
config_version = "1.0.0"
scope = "demografia"

[[facts]]
id = "fact_extra"
dataset = "ibge-sidra-1"
grain = "território x ano"
description = "extra"
fixed_categories = { "Sexo" = "6794" }

[[indicators]]
id = "extra"
name = "Extra"
description = "extra"
dataset = "ibge-sidra-1"
variable = "1"
fact = "fact_extra"
column = "valor"
unit = "Pessoas"
additivity = "non_additive"
concept = "extra"
path = ["Tema"]
"""
    _write(tmp_path / "demografia", fragment, "extra.toml")
    base = load_catalog(tmp_path / "demografia.toml")
    merged = load_scope(tmp_path, "demografia")
    assert len(merged.indicators) == len(base.indicators) + 1
    assert merged.fact("fact_extra").fixed_categories == {"Sexo": "6794"}
    assert merged.content_sha256 != base.content_sha256
    _write(
        tmp_path / "demografia",
        fragment.replace('scope = "demografia"', 'scope = "x"'),
        "extra.toml",
    )
    with pytest.raises(SemanticConfigError, match="escopo"):
        load_scope(tmp_path, "demografia")
    misc = fragment.replace('scope = "demografia"', 'scope = "demografia"\nmisc = 1')
    _write(tmp_path / "demografia", misc, "extra.toml")
    with pytest.raises(SemanticConfigError, match="não aceitas"):
        load_scope(tmp_path, "demografia")
    _write(
        tmp_path / "demografia",
        fragment.replace('"Sexo" = "6794"', '"Cor ou raça" = "95251"').replace(
            'description = "extra"\nfixed',
            'description = "extra"\nclassifications = { "c86" = "k" }\nfixed',
        ),
        "extra.toml",
    )
    with pytest.raises(SemanticConfigError, match="fixas e classificadas"):
        load_scope(tmp_path, "demografia")


def test_repository_scope_with_fragments_matches_sources() -> None:
    from odb_ingestion import load_sources  # noqa: PLC0415

    catalog = load_scope(REPO_INDICATORS, "demografia")
    sources = load_sources(REPO_INDICATORS.parent / "sources")
    missing = [d for d in catalog.datasets() if d not in sources.datasets]
    assert not missing
    assert "despesa_familiar" in {i.id for i in catalog.indicators}


def test_fragment_extends_curated_classification(tmp_path: Path) -> None:
    _write(tmp_path, BASE)
    (tmp_path / "demografia").mkdir()
    ext = """
config_version = "1.0.0"
scope = "demografia"

[[classification_partitions]]
classification = "c2"
id = "p6794_t4418"
label = "Sexo (PNS)"
parent = "6794"
categories = ["110095", "110096"]
exhaustive = false
summable = false
"""
    _write(tmp_path / "demografia", ext, "ext.toml")
    sex = load_scope(tmp_path, "demografia").classification("c2")
    part = next(p for p in sex.partitions if p.id == "p6794_t4418")
    assert part.categories == ("110095", "110096")
    assert part.summable is False
    _write(tmp_path / "demografia", ext.replace('"c2"', '"c999"', 1), "ext.toml")
    with pytest.raises(SemanticConfigError, match="não declarada"):
        load_scope(tmp_path, "demografia")


def test_classification_scoped_to_datasets(tmp_path: Path) -> None:
    """Mesmo nome de dimensão, outros códigos: classificação própria por dataset."""
    from odb_modeling.model import dimension_map  # noqa: PLC0415

    scoped = (
        '[[classifications]]\nid = "sexosim"\nname = "Sexo"\nsilver_dimension = "Sexo"\n'
        'total = "T"\ndatasets = ["datasus-sim-cid10-dores"]\n\n'
    )
    catalog = load_catalog(
        _write(tmp_path, BASE.replace("[[classifications]]", scoped + "[[classifications]]", 1))
    )
    assert dimension_map(catalog)["Sexo"] == "c2"
    assert dimension_map(catalog, "datasus-sim-cid10-dores")["Sexo"] == "sexosim"
    assert dimension_map(catalog, "ibge-sidra-9606")["Sexo"] == "c2"
    # Duas classificações gerais (ou duas no mesmo dataset) para a mesma dimensão: recusado.
    general = scoped.replace('datasets = ["datasus-sim-cid10-dores"]\n', "")
    with pytest.raises(SemanticConfigError, match="mais de uma classificação geral"):
        load_catalog(
            _write(
                tmp_path, BASE.replace("[[classifications]]", general + "[[classifications]]", 1)
            )
        )
