"""Períodos mensais e trimestrais na Gold (chaves AAAA, AAAAMmm e AAAATt)."""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from odb_modeling import model


@pytest.mark.parametrize(
    ("code", "kind", "expected"),
    [
        ("2022", "ano", "2022"),
        ("202609", "mes", "2026M09"),
        ("202512", "mes", "2025M12"),
        ("202602", "trimestre", "2026T2"),
    ],
)
def test_sidra_code_to_gold_key(code: str, kind: str, expected: str) -> None:
    frame = pl.DataFrame({"period": [code]}).select(model.gold_period(kind))
    assert frame["period"][0] == expected


def test_calendar_of_each_period_type() -> None:
    dim = model.build_dim_period(
        pl.DataFrame({"period": ["2026T1", "2024M02", "2022", "2026T4", "2024M12"]})
    )
    rows = {r["period"]: r for r in dim.iter_rows(named=True)}
    assert rows["2022"]["period_type"] == "ano"
    assert (rows["2024M02"]["start_date"], rows["2024M02"]["end_date"]) == (
        date(2024, 2, 1),
        date(2024, 2, 29),
    )
    assert rows["2024M12"]["end_date"] == date(2024, 12, 31)
    assert (rows["2026T1"]["start_date"], rows["2026T1"]["end_date"]) == (
        date(2026, 1, 1),
        date(2026, 3, 31),
    )
    assert rows["2026T4"]["period_type"] == "trimestre"
    assert rows["2026T4"]["end_date"] == date(2026, 12, 31)
    with pytest.raises(ValueError, match="fora dos formatos"):
        model.period_row("202609")  # código SIDRA cru não é chave da Gold
