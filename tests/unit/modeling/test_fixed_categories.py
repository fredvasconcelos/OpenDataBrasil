"""Dimensões de categoria fixa (KPIs de Total do panorama, ADR-0010)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from odb_modeling import model
from odb_semantics import SemanticCatalog, load_catalog
from tests.gold_support import REPO_INDICATORS


def _catalog(tmp_path: Path) -> SemanticCatalog:
    base = (REPO_INDICATORS / "demografia.toml").read_text(encoding="utf-8")
    path = tmp_path / "demografia.toml"
    # O fato da 6579 passa a declarar dimensões fixas (só para o teste).
    path.write_text(
        base.replace(
            'id = "fact_population_estimate"\ndataset = "ibge-sidra-6579"',
            'id = "fact_population_estimate"\ndataset = "ibge-sidra-6579"\n'
            'fixed_categories = { "Sexo" = "6794", "Grupo de idade" = "95253" }',
            1,
        ),
        encoding="utf-8",
    )
    return load_catalog(path)


def _rows(categories: list[tuple[str, str]], fact: str = "fact_population_estimate") -> Any:
    return {
        "fact_table": fact,
        "classification_key": ";".join(f"{d}={c}" for d, c in categories),
        "classifications": [
            {"dimension": d, "category_id": c, "category_name": "x"} for d, c in categories
        ],
    }


def test_fixed_dimensions_are_checked_and_removed(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    selected = pl.DataFrame(
        [
            _rows([("Sexo", "6794"), ("Grupo de idade", "95253")]),
            _rows([("Cor ou raça", "95251")], fact="fact_population_by_race"),
        ]
    )
    stripped, problems = model.strip_fixed_categories(selected, catalog)
    assert problems == {}
    assert stripped["classifications"].to_list()[0] == []
    # Outros fatos ficam intactos.
    assert stripped["classifications"].to_list()[1][0]["dimension"] == "Cor ou raça"


def test_other_category_or_missing_dimension_is_reported(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    selected = pl.DataFrame(
        [_rows([("Sexo", "6794")]), _rows([("Sexo", "4")])],
    )
    _, problems = model.strip_fixed_categories(selected, catalog)
    assert problems == {"fact_population_estimate": {"Sexo": ["4", "6794"], "Grupo de idade": []}}


def test_unit_check_ignores_missing_values_without_unit(tmp_path: Path) -> None:
    """Sem valor ("...") a fonte não informa unidade; só valores publicados contam."""
    from odb_modeling.model import DatasetInfo  # noqa: PLC0415
    from odb_modeling.quality import input_checks  # noqa: PLC0415

    catalog = load_catalog(REPO_INDICATORS / "demografia.toml")
    datasets = {
        d: DatasetInfo(d, d.removeprefix("ibge-sidra-"), None, "ibge-reuso-com-citacao")
        for d in catalog.datasets()
    }

    def rows(units: list[tuple[str, str]]) -> pl.DataFrame:
        return pl.DataFrame(
            [
                {
                    "table_id": "6579",
                    "variable_id": "9324",
                    "unit_name": unit,
                    "value_status": status,
                    "territorial_level": "1",
                    "indicator_id": "populacao_estimada",
                    "fact_table": "fact_population_estimate",
                    **_rows([]),
                }
                for unit, status in units
            ],
            schema_overrides={
                "classifications": pl.List(
                    pl.Struct(
                        {
                            "dimension": pl.String,
                            "category_id": pl.String,
                            "category_name": pl.String,
                        }
                    )
                )
            },
        )

    def unit_check(frame: pl.DataFrame) -> str:
        checks = input_checks(frame, catalog, datasets, [])
        return next(c.status.value for c in checks if c.check_id == "semantics.unit")

    assert unit_check(rows([("Pessoas", "valid"), ("", "not_available")])) == "pass"
    assert unit_check(rows([("Pessoas", "valid"), ("", "valid")])) == "fail"
    assert unit_check(rows([("Pessoas", "valid"), ("Mil pessoas", "valid")])) == "fail"
