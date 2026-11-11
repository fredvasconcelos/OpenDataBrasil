"""Comparação SIM vs. Registro Civil (``odb fontes comparar-obitos``)."""

from __future__ import annotations

import polars as pl

from odb_cli.fontes import compare, render, state_totals

CLASS = pl.List(
    pl.Struct({"dimension": pl.String, "category_id": pl.String, "category_name": pl.String})
)


def _obs(table: str, var: str, rows: list[tuple[str, str, str, str, float]]) -> pl.LazyFrame:
    return pl.DataFrame(
        {
            "table_id": [table] * len(rows),
            "variable_id": [var] * len(rows),
            "territorial_level": [r[0] for r in rows],
            "territory_id": [r[1] for r in rows],
            "period": [r[2] for r in rows],
            "classifications": [
                [{"dimension": "Sexo", "category_id": r[3], "category_name": "x"}] for r in rows
            ],
            "value": [r[4] for r in rows],
        },
        schema_overrides={"classifications": CLASS},
    ).lazy()


def test_compare_states_and_brazil() -> None:
    sim = state_totals(
        _obs(
            "SIM-DORES",
            "obitos",
            [
                ("3", "12", "2023", "T", 110.0),
                ("3", "12", "2023", "1", 60.0),
                ("3", "35", "2023", "T", 300.0),
            ],
        ),
        "SIM-DORES",
        "obitos",
    )
    # SIM sem nível Brasil: soma das UFs.
    assert sim.filter(pl.col("territorial_level") == "1")["value"].to_list() == [410.0]
    civil = pl.DataFrame(
        {
            "territorial_level": ["3", "3", "1"],
            "territory_id": ["12", "35", "1"],
            "period": ["2023"] * 3,
            "value": [100.0, 300.0, 400.0],
        }
    )
    table = compare(sim, civil)
    ac = table.filter(pl.col("territory_id") == "12").row(0, named=True)
    assert round(ac["razao_pct"], 1) == 110.0
    doc = render(table, "2026-11-11")
    assert "| 2023 | 410 | 400 | 102.5% |" in doc
    assert "| AC | 110.0%" in doc
    assert "Diferença de até 2.0%: 1 (50%)" in doc
