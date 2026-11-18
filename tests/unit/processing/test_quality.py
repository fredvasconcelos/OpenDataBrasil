import json
from datetime import UTC, datetime

import polars as pl
import pytest

from odb_processing.contracts import DTB_MUNICIPALITY, SIDRA_OBSERVATION
from odb_processing.parsers import Lineage, parse_dtb_municipalities, parse_sidra
from odb_processing.quality import (
    CheckStatus,
    blocking,
    check_reconciliation,
    check_territorial_reference,
    dtb_checks,
    sidra_checks,
)
from tests.ingestion_support import DTB_FIXTURES, SIDRA_FIXTURES

LINEAGE = Lineage(
    "a",
    "b" * 64,
    "u",
    datetime(2026, 11, 3, tzinfo=UTC),
    "i",
    "r",
    datetime(2026, 11, 3, tzinfo=UTC),
)


def _frame(name: str, table: str, mutate: object = None) -> pl.DataFrame:
    payload = json.loads((SIDRA_FIXTURES / name).read_text("utf-8"))
    if mutate:
        mutate(payload)  # type: ignore[operator]
    return parse_sidra(json.dumps(payload).encode(), table_id=table, lineage=LINEAGE)


def _by_id(results: list) -> dict:  # type: ignore[type-arg]
    return {r.check_id: r for r in results}


def test_real_data_reconciles_between_official_levels() -> None:
    """Dados reais: UFs e regiões somam o total do Brasil (2004 inclusive)."""
    for name in ("t6579_n1n2n3_p2025.json", "t6579_n1n2n3_p2004.json"):
        results = _by_id(check_reconciliation(_frame(name, "6579"), {"9324": "exact"}))
        assert {k: r.status for k, r in results.items()} == {
            "reconciliation.9324.n3_n1": CheckStatus.PASS,
            "reconciliation.9324.n2_n1": CheckStatus.PASS,
            "reconciliation.9324.n3_n2": CheckStatus.PASS,
        }


def test_area_needs_rounding_tolerance_and_density_is_never_summed() -> None:
    census = _frame("t4714_n1n2n3_p2022.json", "4714")
    exact = _by_id(check_reconciliation(census, {"6318": "exact"}))
    assert (
        exact["reconciliation.6318.n3_n1"].status is CheckStatus.WARN
    )  # 0,003 km² de arredondamento
    rounding = _by_id(check_reconciliation(census, {"93": "exact", "6318": "rounding"}))
    assert all(r.status is CheckStatus.PASS for r in rounding.values())
    assert not any(k.startswith("reconciliation.614") for k in rounding)


def test_divergence_is_warning_with_details() -> None:
    def inflate_sp(payload: list[dict[str, str]]) -> None:
        for row in payload[1:]:
            if row["NC"] == "3" and row["D1C"] == "35":
                row["V"] = str(int(row["V"]) + 11968)

    results = _by_id(
        check_reconciliation(
            _frame("t6579_n1n2n3_p2025.json", "6579", inflate_sp), {"9324": "exact"}
        )
    )
    warn = results["reconciliation.9324.n3_n1"]
    assert warn.status is CheckStatus.WARN
    assert warn.details["divergent"][0]["difference"] == "11968.000000"
    assert results["reconciliation.9324.n3_n2"].status is CheckStatus.WARN
    assert not blocking(list(results.values()))


def test_not_available_is_excluded_not_zeroed() -> None:
    def blank_ac(payload: list[dict[str, str]]) -> None:
        for row in payload[1:]:
            if row["NC"] == "3" and row["D1C"] == "12":
                row["V"] = "..."

    results = _by_id(
        check_reconciliation(_frame("t6579_n1n2n3_p2025.json", "6579", blank_ac), {"9324": "exact"})
    )
    # Sem o valor do AC, a soma das UFs fica abaixo do Brasil: grupo incompleto, não divergente.
    incomplete = results["reconciliation.9324.n3_n1"]
    assert incomplete.status is CheckStatus.PASS
    assert incomplete.details["incomplete"] == 1
    assert "incompletos" in incomplete.message
    assert results["reconciliation.9324.n2_n1"].status is CheckStatus.PASS

    def blank_ac_and_inflate_sp(payload: list[dict[str, str]]) -> None:
        blank_ac(payload)
        for row in payload[1:]:
            if row["NC"] == "3" and row["D1C"] == "35":
                row["V"] = str(int(row["V"]) + 10_000_000)

    # Com valor suprimido, a soma conhecida ainda não pode passar do total oficial.
    exceeded = _by_id(
        check_reconciliation(
            _frame("t6579_n1n2n3_p2025.json", "6579", blank_ac_and_inflate_sp), {"9324": "exact"}
        )
    )["reconciliation.9324.n3_n1"]
    assert exceeded.status is CheckStatus.WARN
    assert exceeded.details["divergent"][0]["children_without_value"] == 1
    assert (
        check_reconciliation(_frame("t6579_n1n2n3_p2025.json", "6579"), {"999": "exact"})[0].status
        is CheckStatus.WARN
    )


def test_sidra_blocking_checks() -> None:
    ok = _frame("t6579_n1n2n3_p2025.json", "6579")
    assert not blocking(sidra_checks(ok, SIDRA_OBSERVATION, {"9324": "exact"}, None, "dtb"))

    dup = pl.concat([ok, ok.head(1)])
    assert "unique.key" in {
        c.check_id for c in blocking(sidra_checks(dup, SIDRA_OBSERVATION, {}, None, "x"))
    }
    bad_code = ok.with_columns(
        pl.when(pl.col("territorial_level") == "3")
        .then(pl.lit("999"))
        .otherwise(pl.col("territory_id"))
        .alias("territory_id")
    )
    assert "domain.territory_id" in {
        c.check_id for c in blocking(sidra_checks(bad_code, SIDRA_OBSERVATION, {}, None, "x"))
    }
    conv = _frame("t6579_n1n2n3_p2025.json", "6579", lambda p: p[1].__setitem__("V", "1,5"))
    assert "values.conversion_error" in {
        c.check_id for c in blocking(sidra_checks(conv, SIDRA_OBSERVATION, {}, None, "x"))
    }
    nulls = ok.with_columns(pl.lit(None, dtype=pl.String).alias("source_url"))
    assert "not_null.required" in {
        c.check_id for c in blocking(sidra_checks(nulls, SIDRA_OBSERVATION, {}, None, "x"))
    }
    wrong = ok.drop("value_decimals")
    only = sidra_checks(wrong, SIDRA_OBSERVATION, {}, None, "x")
    assert [c.check_id for c in only] == ["schema.contract"]
    assert only[0].status is CheckStatus.FAIL


def test_territorial_reference() -> None:
    rows = pl.DataFrame(
        {
            "territorial_level": ["6", "6", "6", "3"],
            "territory_id": ["1100015", "5101837", "9999999", "11"],
            "value_status": ["valid", "not_available", "valid", "valid"],
        }
    )
    assert check_territorial_reference(rows, None, "dtb").status is CheckStatus.WARN
    missing = check_territorial_reference(rows, {"1100015"}, "dtb 2025")
    assert missing.status is CheckStatus.WARN
    assert missing.details["missing"] == ["9999999"]  # 5101837 é "...": não exige referência
    assert (
        check_territorial_reference(rows, {"1100015", "9999999"}, "dtb").status is CheckStatus.PASS
    )
    assert (
        check_territorial_reference(
            rows.filter(pl.col("territorial_level") == "3"), set(), "dtb"
        ).status
        is CheckStatus.PASS
    )


@pytest.fixture(scope="module")
def dtb() -> pl.DataFrame:
    ods = DTB_FIXTURES / "RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.ods"
    return parse_dtb_municipalities(
        ods.read_bytes(), member=ods.name, reference_year="2025", lineage=LINEAGE
    )


def test_dtb_checks(dtb: pl.DataFrame) -> None:
    results = _by_id(dtb_checks(dtb, DTB_MUNICIPALITY))
    assert all(r.status is CheckStatus.PASS for r in results.values()), results
    broken = dtb.with_columns(
        pl.when(pl.col("municipality_id") == "1100015")
        .then(pl.lit("1200015"))
        .otherwise(pl.col("municipality_id"))
        .alias("municipality_id")
    )
    assert (
        _by_id(dtb_checks(broken, DTB_MUNICIPALITY))["domain.municipality_id"].status
        is CheckStatus.FAIL
    )
    fewer = dtb.filter(pl.col("uf_id") != "53")
    assert _by_id(dtb_checks(fewer, DTB_MUNICIPALITY))["coverage.uf"].status is CheckStatus.WARN
    assert [c.check_id for c in dtb_checks(dtb.drop("source_member"), DTB_MUNICIPALITY)] == [
        "schema.contract"
    ]
