"""Séries compostas de fontes distintas (ADR-0022): transformações por tabela."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import polars as pl

from odb_modeling import model
from odb_semantics import load_scope
from odb_semantics.config import AggregateRule, GroupDimensionRule, TableRule

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
    assert other["value_raw"] == "..."


def test_groups_skip_parts_not_surveyed() -> None:
    """Grupos de lavoura: produto "..." (não pesquisado no ano) fica fora da soma."""
    rule = TableRule(
        aggregate=(
            AggregateRule(
                dimension=DIM,
                target="g_graos",
                name="Grãos",
                sources=("1", "2", "3"),
                ignore_unavailable=True,
            ),
        )
    )

    def group(rows: list[dict[str, Any]]) -> dict[str, Any]:
        out = model.apply_table_transforms(_frame(rows), _catalog(rule))
        return out.filter(pl.col("classification_key") == f"{DIM}=g_graos").row(0, named=True)

    na = [_row("6805", "6", "3", 0, "not_available")]
    summed = group([_row("6805", "6", "1", 12), _row("6805", "6", "2", 0, "true_zero"), *na])
    assert summed["value"] == 12
    assert summed["value_status"] == "valid"
    suppressed = group([_row("6805", "6", "1", 12), _row("6805", "6", "2", 0, "suppressed"), *na])
    assert suppressed["value"] is None
    nothing = group([_row("6805", "6", "1", 0, "not_available"), *na])
    assert nothing["value"] is None
    assert nothing["value_status"] == "not_available"


def test_group_dimension_crosses_group_and_product() -> None:
    """Grupo de lavoura como classificação própria: grupo, produto ou os dois."""
    rule = TableRule(
        group_dimension=GroupDimensionRule(
            dimension=DIM,
            name="Grupo",
            total="0",
            groups=(AggregateRule(dimension=DIM, target="g_a", name="A", sources=("1", "2")),),
        )
    )
    rows = [_row("6805", "6", c, v) for c, v in (("0", 30), ("1", 10), ("2", 20), ("9", 0))]
    out = model.apply_table_transforms(_frame(rows), _catalog(rule))
    got = {(r["classification_key"]): float(r["value"]) for r in out.iter_rows(named=True)}
    assert got == {
        f"{DIM}=0;Grupo=0": 30,  # Total
        f"{DIM}=1;Grupo=0": 10,  # produto, sem grupo
        f"{DIM}=2;Grupo=0": 20,
        f"{DIM}=9;Grupo=0": 0,  # fora dos grupos (subproduto): só no Total
        f"{DIM}=1;Grupo=g_a": 10,  # produto dentro do grupo
        f"{DIM}=2;Grupo=g_a": 20,
        f"{DIM}=0;Grupo=g_a": 30,  # o grupo: soma dos produtos
    }


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


def test_ipca_preserva_brasil_e_seleciona_apenas_indice_geral_das_areas() -> None:
    """A ampliação territorial não duplica o Brasil nem soma os grupos do IPCA."""
    catalog = load_scope(Path(__file__).parents[3] / "configs/indicators", "demografia")
    dimension = "Geral, grupo, subgrupo, item e subitem"
    rows = []
    for table, level, category, value in (
        ("1737", "1", None, 0.26),
        ("7060", "1", "7169", 0.26),
        ("7060", "6", "7169", 0.45),
        ("7060", "6", "7170", 1.20),
        ("7060", "7", "7169", 0.33),
    ):
        row = _row(table, level, "0", value)
        row.update(fact_table="fact_sidra_1737", variable_id="63")
        row["classifications"] = (
            [{"dimension": dimension, "category_id": category, "category_name": category}]
            if category
            else []
        )
        row["classification_key"] = f"{dimension}={category}" if category else ""
        rows.append(row)
    selected = model.apply_table_transforms(_frame(rows), catalog)
    out, problems = model.strip_fixed_categories(selected, catalog)
    assert not problems
    assert {
        (r["table_id"], r["territorial_level"]): float(r["value"])
        for r in out.iter_rows(named=True)
    } == {
        ("1737", "1"): 0.26,
        ("7060", "6"): 0.45,
        ("7060", "7"): 0.33,
    }
    assert out["classifications"].list.len().to_list() == [0, 0, 0]


def test_excluded_periods_leave_the_year_to_the_other_source() -> None:
    rows = [_row("7113", "1", "46292", 5.6), {**_row("7113", "1", "46292", 6.0), "period": "2023"}]
    out = model.apply_table_transforms(
        _frame(rows), _catalog(TableRule(exclude_periods=("2022",)), "7113")
    )
    assert out["period"].to_list() == ["2023"]


def test_keep_categories_filters_rows() -> None:
    rows = [_row("7113", "1", "2795", 5.6), _row("7113", "1", "3302", 16.0)]
    out = model.apply_table_transforms(
        _frame(rows), _catalog(TableRule(keep_categories={DIM: ("2795",)}), "7113")
    )
    assert out["classification_key"].to_list() == [f"{DIM}=2795"]


def test_month_dimension_becomes_monthly_period() -> None:
    """Óbitos (2654): "Mês de ocorrência" vira o período; Total e Ignorado saem."""
    month = "Mês de ocorrência"

    def row(cat: str, name: str, value: float) -> dict[str, Any]:
        r = _row("2654", "1", "0", value)
        r["period"] = "2021"
        r["classifications"] = [
            {"dimension": month, "category_id": cat, "category_name": name},
            {"dimension": DIM, "category_id": "0", "category_name": "Total"},
        ]
        return r

    rows = [
        row("0", "Total", 30),
        row("5593", "Agosto", 12),
        row("5594", "Setembro", 18),
        row("9", "Ignorado", 0),
    ]
    out = model.apply_table_transforms(
        _frame(rows), _catalog(TableRule(month_dimension=month), "2654")
    )
    assert sorted(zip(out["period"], out["value"].cast(float), strict=True)) == [
        ("2021M08", 12.0),
        ("2021M09", 18.0),
    ]
    assert all(month not in k for k in out["classification_key"])
