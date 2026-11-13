"""Séries compostas de fontes distintas (ADR-0022): transformações por tabela."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import polars as pl

from odb_modeling import model
from odb_semantics.config import AggregateRule, TableRule

DIM = "Tipo de esgotamento sanitário"


def _row(table: str, level: str, cat: str, value: float, status: str = "valid") -> dict[str, Any]:
    return {
        "fact_table": "f",
        "table_id": table,
        "variable_id": "381",
        "unit_name": "Unidades",
        "territorial_level": level,
        "territory_id": "1" if level == "1" else "2927408",
        "period": "2022",
        "classification_key": f"{DIM}={cat}",
        "classifications": [{"dimension": DIM, "category_id": cat, "category_name": cat}],
        "value_raw": str(value),
        "value": Decimal(str(value)),
        "value_status": status,
        "value_decimals": 0,
        "bronze_artifact_id": "a",
        "bronze_checksum_sha256": "s",
    }


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema_overrides={"value": pl.Decimal(38, 6)})


def _catalog(rule: TableRule, table: str = "6805") -> Any:
    return SimpleNamespace(facts=[SimpleNamespace(id="f", table_rules={table: rule})])


def test_censo_sewage_harmonized_to_pnad_groups() -> None:
    """Censo 2022 no município: "Outro tipo" somado, sem banheiro e agregados fora."""
    rule = TableRule(
        levels=("6",),
        aggregate=(
            AggregateRule(
                dimension=DIM,
                target="119522",
                name="Outro tipo",
                sources=("72113", "92858", "72114", "72115"),
            ),
            AggregateRule(
                dimension=DIM,
                target="46292",
                name="Total",
                sources=("72110", "72111", "72112", "72113", "92858", "72114", "72115"),
            ),
        ),
        drop_categories={DIM: ("46292", "46290", "92861", "72113", "92858", "72114", "72115")},
    )
    cats = {
        "46292": 100,
        "46290": 60,
        "72110": 50,
        "72111": 10,
        "72112": 15,
        "72113": 12,
        "92858": 3,
        "72114": 4,
        "72115": 1,
        "92861": 5,
    }
    rows = [_row("6805", "6", c, v) for c, v in cats.items()] + [_row("6805", "1", "46292", 999)]
    out = model.apply_table_transforms(_frame(rows), _catalog(rule))
    got = {
        r["classification_key"].split("=")[1]: float(r["value"]) for r in out.iter_rows(named=True)
    }
    # Brasil fora (só o município); Total sem os 5 sem banheiro; "Outro tipo" = 12+3+4+1.
    assert got == {"72110": 50.0, "72111": 10.0, "72112": 15.0, "119522": 20.0, "46292": 95.0}
    assert set(out["territorial_level"]) == {"6"}


def test_sum_without_all_parts_has_no_value() -> None:
    rule = TableRule(
        aggregate=(
            AggregateRule(
                dimension=DIM, target="119522", name="Outro tipo", sources=("72113", "92858")
            ),
        )
    )
    rows = [_row("6805", "6", "72113", 12), _row("6805", "6", "92858", 0, "suppressed")]
    out = model.apply_table_transforms(_frame(rows), _catalog(rule))
    other = out.filter(pl.col("classification_key") == f"{DIM}=119522").row(0, named=True)
    assert other["value"] is None
    assert other["value_status"] == "not_available"


def test_scale_unit_and_complement() -> None:
    scaled = model.apply_table_transforms(
        _frame([_row("7192", "3", "46292", 4.581)]),
        _catalog(TableRule(scale=1000, unit="Unidades"), "7192"),
    )
    assert float(scaled["value"][0]) == 4581.0
    assert scaled["unit_name"][0] == "Unidades"
    rate = model.apply_table_transforms(
        _frame([_row("7113", "1", "46292", 5.6)]),
        _catalog(TableRule(complement=100.0, unit="%"), "7113"),
    )
    assert float(rate["value"][0]) == 94.4


def test_tables_without_transforms_are_untouched() -> None:
    frame = _frame([_row("9999", "1", "46292", 1)])
    assert model.apply_table_transforms(frame, _catalog(TableRule(levels=("6",)))).equals(frame)


def test_excluded_periods_leave_the_year_to_the_other_source() -> None:
    rows = [_row("7113", "1", "46292", 5.6), {**_row("7113", "1", "46292", 6.0), "period": "2023"}]
    out = model.apply_table_transforms(
        _frame(rows), _catalog(TableRule(exclude_periods=("2022",)), "7113")
    )
    assert out["period"].to_list() == ["2023"]
