"""Grandes Regiões pela soma das UFs (Sinesp VDE publica Brasil, UFs e municípios)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import polars as pl

from odb_modeling import model


def _obs(
    geo: str, value: float | None, status: str = "valid", period: str = "2025M01"
) -> dict[str, Any]:
    return {
        "indicator_id": "fem",
        "dataset_id": "vde",
        "geography_key": geo,
        "level_id": geo.split(":", maxsplit=1)[0],
        "period": period,
        "breakdown_key": "none",
        "value": None if value is None else Decimal(str(value)),
        "value_status": status,
        "value_raw": str(value),
        "value_decimals": 0,
        "unit": "Vítimas",
        "flags": [],
        "source_table_id": "VDE-2025",
        "source_variable_id": "feminicidio",
        "silver_table_version": 1,
        "bronze_artifact_id": "a",
        "bronze_checksum_sha256": "s",
        "gold_build_id": "b",
    }


def _catalog(levels: tuple[str, ...] = ("regiao",)) -> Any:
    return SimpleNamespace(indicators=[SimpleNamespace(id="fem", derived_levels=levels)])


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema_overrides={"value": pl.Decimal(38, 6)})


def test_regions_are_the_sum_of_their_ufs() -> None:
    rows = [
        _obs("uf:29", 10),
        _obs("uf:28", 3),
        _obs("uf:35", 20),
        _obs("brasil:1", 33),
        _obs("municipio:2927408", 4),
    ]
    out = model.derive_regions(_frame(rows), _catalog())
    regions = {
        r["geography_key"]: (float(r["value"]), r["value_status"], r["flags"])
        for r in out.filter(pl.col("level_id") == "regiao").iter_rows(named=True)
    }
    # Nordeste = BA + SE; Sudeste = SP (o primeiro dígito da UF é a região).
    assert regions == {
        "regiao:2": (13.0, "derived_sum", ["derived_region"]),
        "regiao:3": (20.0, "derived_sum", ["derived_region"]),
    }
    assert out.height == len(rows) + 2


def test_region_without_all_ufs_published_has_no_value() -> None:
    out = model.derive_regions(
        _frame([_obs("uf:17", None, "not_available"), _obs("uf:15", 5)]), _catalog()
    )
    north = out.filter(pl.col("geography_key") == "regiao:1").row(0, named=True)
    assert north["value"] is None
    assert north["value_status"] == "incomplete_sum"


def test_indicators_without_derived_levels_are_untouched() -> None:
    frame = _frame([_obs("uf:29", 10)])
    assert model.derive_regions(frame, _catalog(())).equals(frame)
