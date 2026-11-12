"""Períodos mensais e trimestrais na Gold (chaves AAAA, AAAAMmm e AAAATt)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

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


def test_dim_period_brings_the_larger_periods_and_the_bridge() -> None:
    """Um mês observado traz trimestre, semestre e ano, com rótulos (ADR-0013)."""
    observed = pl.DataFrame({"period": ["2024M05", "2024M06", "2022"]})
    dim = model.build_dim_period(observed)
    rows = {r["period"]: r for r in dim.iter_rows(named=True)}
    assert set(rows) == {"2024M05", "2024M06", "2024T2", "2024S1", "2024", "2022"}
    assert (rows["2024M05"]["month"], rows["2024M05"]["quarter"]) == (5, 2)
    assert (rows["2024T2"]["label"], rows["2024T2"]["short_label"]) == (
        "2º trimestre de 2024",
        "T2 2024",
    )
    assert rows["2024S1"]["semester"] == 1
    assert rows["2022"]["month"] is None
    bridge = model.build_bridge_period_ancestor(observed)
    may = {
        r["ancestor_type"]: r
        for r in bridge.filter(pl.col("period") == "2024M05").iter_rows(named=True)
    }
    assert {t: (r["ancestor_period"], r["parts"]) for t, r in may.items()} == {
        "trimestre": ("2024T2", 3),
        "semestre": ("2024S1", 6),
        "ano": ("2024", 12),
    }
    # O ano publicado não tem período maior.
    assert bridge.filter(pl.col("period") == "2022").is_empty()


def test_first_period_cuts_gold_not_silver(tmp_path: Path) -> None:
    from odb_semantics import load_catalog  # noqa: PLC0415
    from tests.gold_support import REPO_INDICATORS  # noqa: PLC0415

    base = (REPO_INDICATORS / "demografia.toml").read_text(encoding="utf-8")
    path = tmp_path / "demografia.toml"
    path.write_text(
        base.replace(
            'id = "populacao_estimada"\n', 'id = "populacao_estimada"\nfirst_period = "2010"\n', 1
        ),
        encoding="utf-8",
    )
    catalog = load_catalog(path)
    silver = pl.DataFrame(
        {"table_id": ["6579"] * 3, "variable_id": ["9324"] * 3, "period": ["2009", "2010", "2024"]}
    )
    mapping = pl.DataFrame(
        {"table_id": ["6579"], "variable_id": ["9324"], "indicator_id": ["populacao_estimada"]}
    )
    kept = model.select_silver(silver, mapping, catalog)
    assert kept["period"].to_list() == ["2010", "2024"]
    # Mensal: o corte por ano vale para os códigos AAAAMM.
    monthly = silver.with_columns(pl.Series("period", ["199712", "199801", "202609"]))
    assert model.select_silver(
        monthly,
        mapping,
        catalog.model_copy(
            update={
                "indicators": tuple(
                    i.model_copy(update={"first_period": "1998"})
                    if i.id == "populacao_estimada"
                    else i
                    for i in catalog.indicators
                )
            }
        ),
    )["period"].to_list() == ["199801", "202609"]


def test_indicator_map_expands_dataset_series() -> None:
    """Série (Sinesp VDE, um dataset por ano): uma linha por tabela anual."""
    from odb_semantics.config import load_catalog  # noqa: PLC0415

    catalog = load_catalog(
        Path(__file__).parents[3]
        / "configs"
        / "indicators"
        / "demografia"
        / "seguranca_sinesp.toml"
    )
    series = model.DatasetInfo(
        "mjsp-sinesp-vde",
        "SINESP-VDE",
        None,
        "mjsp-dados-abertos",
        period_type="mes",
        table_ids=("SINESP-VDE-2015", "SINESP-VDE-2016"),
    )
    assert series.source_tables == ("SINESP-VDE-2015", "SINESP-VDE-2016")
    mapping = model.indicator_map(catalog, {"mjsp-sinesp-vde": series})
    homicide = mapping.filter(pl.col("indicator_id") == "sinesp_homicidio_doloso")
    assert sorted(homicide["table_id"]) == ["SINESP-VDE-2015", "SINESP-VDE-2016"]
    assert set(mapping["dataset_id"]) == {"mjsp-sinesp-vde"}
    # Dataset único continua com a própria tabela.
    single = model.DatasetInfo("ibge-sidra-6579", "6579", None, "x")
    assert single.source_tables == ("6579",)
