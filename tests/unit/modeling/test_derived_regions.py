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
    return pl.DataFrame(
        rows, schema_overrides={"value": pl.Decimal(38, 6), "flags": pl.List(pl.String)}
    )


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


def test_regiao_com_uf_indisponivel_preserva_soma_parcial() -> None:
    out = model.derive_regions(
        _frame([_obs("uf:17", None, "not_available"), _obs("uf:15", 5)]), _catalog()
    )
    north = out.filter(pl.col("geography_key") == "regiao:1").row(0, named=True)
    assert north["value"] == 5
    assert north["value_status"] == "partial_sum"
    assert "partial_coverage" in north["flags"]


def test_indicators_without_derived_levels_are_untouched() -> None:
    frame = _frame([_obs("uf:29", 10)])
    assert model.derive_regions(frame, _catalog(())).equals(frame)


SOUTH = {"regiao:4": ("uf:41", "uf:42", "uf:43")}


def test_regiao_completa_confere_com_todas_as_ufs_da_referencia() -> None:
    out = model.derive_regions(
        _frame([_obs("uf:41", 10), _obs("uf:42", 20), _obs("uf:43", 30)]), _catalog(), SOUTH
    )
    region = out.filter(pl.col("level_id") == "regiao").row(0, named=True)
    assert region["value"] == 60
    assert region["value_status"] == "derived_sum"


def test_uf_inteiramente_ausente_nao_vira_zero() -> None:
    out = model.derive_regions(_frame([_obs("uf:41", 10), _obs("uf:43", 30)]), _catalog(), SOUTH)
    region = out.filter(pl.col("level_id") == "regiao").row(0, named=True)
    assert region["value"] == 40
    assert region["value_status"] == "partial_sum"
    assert "incomplete_geography" in region["flags"]


def test_regiao_sem_nenhuma_uf_observada_continua_sem_valor() -> None:
    reference = {**SOUTH, "regiao:3": ("uf:31", "uf:32", "uf:33", "uf:35")}
    out = model.derive_regions(_frame([_obs("uf:35", 10)]), _catalog(), reference)
    south = out.filter(pl.col("geography_key") == "regiao:4").row(0, named=True)
    assert south["value"] is None
    assert south["value_status"] == "incomplete_sum"


def test_sigilo_preservado_com_soma_parcial_das_ufs_publicadas() -> None:
    out = model.derive_regions(
        _frame([_obs("uf:41", None, "suppressed"), _obs("uf:42", 20), _obs("uf:43", 30)]),
        _catalog(),
        SOUTH,
    )
    region = out.filter(pl.col("level_id") == "regiao").row(0, named=True)
    assert region["value"] == 50
    assert region["value_status"] == "partial_sum"
    assert region["value_raw"] == "50.000000"
    assert "contains_suppressed" in region["flags"]
    assert out.filter(pl.col("geography_key") == "uf:41")["value_status"][0] == "suppressed"


def test_regiao_sem_nenhum_numero_publicado_nao_fabrica_zero() -> None:
    out = model.derive_regions(
        _frame([_obs("uf:41", None, "suppressed"), _obs("uf:42", None, "not_available")]),
        _catalog(),
        SOUTH,
    )
    region = out.filter(pl.col("level_id") == "regiao").row(0, named=True)
    assert region["value"] is None
    assert region["value_status"] == "suppressed"
    assert region["value_raw"] == "X"


def test_uf_ambigua_nao_duplica_o_valor_na_soma_parcial() -> None:
    out = model.derive_regions(
        _frame([_obs("uf:41", 10), _obs("uf:41", 12), _obs("uf:42", 20)]),
        _catalog(),
        SOUTH,
    )
    region = out.filter(pl.col("level_id") == "regiao").row(0, named=True)
    assert region["value"] == 20
    assert region["value_status"] == "partial_sum"


def test_total_regional_nativo_prevalece_sobre_derivado() -> None:
    original = _obs("regiao:4", 61)
    out = model.derive_regions(
        _frame([_obs("uf:41", 10), _obs("uf:42", 20), _obs("uf:43", 30), original]),
        _catalog(),
        SOUTH,
    )
    regions = out.filter(pl.col("level_id") == "regiao")
    assert regions.height == 1
    assert regions["value"][0] == 61
    assert regions["flags"][0].to_list() == []


def test_linhagem_representativa_pertence_a_uma_uf_da_propria_regiao() -> None:
    """O arquivo de São Paulo não representa os componentes do Sul no SIM."""
    sp = {**_obs("uf:35", 20), "bronze_artifact_id": "arquivo-sp", "bronze_checksum_sha256": "sp"}
    pr = {**_obs("uf:41", 10), "bronze_artifact_id": "arquivo-pr", "bronze_checksum_sha256": "pr"}
    out = model.derive_regions(
        _frame([sp, pr]), _catalog(), {"regiao:3": ["uf:35"], "regiao:4": ["uf:41"]}
    )
    south = out.filter(pl.col("geography_key") == "regiao:4").row(0, named=True)
    assert south["bronze_artifact_id"] == "arquivo-pr"
    assert south["bronze_checksum_sha256"] == "pr"
