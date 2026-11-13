"""Hierarquia de períodos e agregação no tempo (ADR-0013)."""

from __future__ import annotations

from datetime import date

import duckdb
import pytest

from odb_semantics import IndicatorMeta, IndicatorQuery, SemanticError, plan_query
from odb_semantics.periods import (
    PeriodError,
    ancestor,
    coarser_grains,
    complete_periods_at,
    parse_period,
    parts,
    periods_at,
)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("2024M01", ("mes", "janeiro de 2024", "jan 2024", date(2024, 1, 1), date(2024, 1, 31))),
        ("2024M02", ("mes", "fevereiro de 2024", "fev 2024", date(2024, 2, 1), date(2024, 2, 29))),
        (
            "2024T1",
            ("trimestre", "1º trimestre de 2024", "T1 2024", date(2024, 1, 1), date(2024, 3, 31)),
        ),
        (
            "2024T4",
            ("trimestre", "4º trimestre de 2024", "T4 2024", date(2024, 10, 1), date(2024, 12, 31)),
        ),
        (
            "2024S2",
            ("semestre", "2º semestre de 2024", "S2 2024", date(2024, 7, 1), date(2024, 12, 31)),
        ),
        ("2024", ("ano", "2024", "2024", date(2024, 1, 1), date(2024, 12, 31))),
    ],
)
def test_labels_and_calendar(code: str, expected: tuple[object, ...]) -> None:
    p = parse_period(code)
    assert (p.grain, p.label, p.short_label, p.start, p.end) == expected


def test_position_in_the_hierarchy() -> None:
    may = parse_period("2024M05")
    assert (may.month, may.quarter, may.semester) == (5, 2, 1)
    assert ancestor("2024M05", "trimestre") == "2024T2"
    assert ancestor("2024M05", "semestre") == "2024S1"
    assert ancestor("2024M12", "ano") == "2024"
    assert ancestor("2024T3", "semestre") == "2024S2"
    assert coarser_grains("trimestre") == ("trimestre", "semestre", "ano")
    assert (parts("mes", "trimestre"), parts("mes", "ano"), parts("trimestre", "ano")) == (3, 12, 4)
    with pytest.raises(PeriodError):
        ancestor("2024", "mes")  # não se desagrega
    with pytest.raises(PeriodError, match="fora dos formatos"):
        parse_period("202405")


def test_complete_periods_leave_out_the_open_year() -> None:
    months = [f"2025M{m:02d}" for m in range(1, 13)] + [f"2026M{m:02d}" for m in range(1, 10)]
    assert periods_at(months, "ano") == ["2025", "2026"]
    assert complete_periods_at(months, "ano") == ["2025"]
    assert complete_periods_at(months, "trimestre")[-1] == "2026T3"
    assert "2026T4" not in periods_at(months, "trimestre")
    assert complete_periods_at(months, "semestre") == ["2025S1", "2025S2", "2026S1"]


LEVELS = ("brasil", "uf")
FLOW = IndicatorMeta(
    "vitimas", "Vítimas", "Vítimas", "additive", "vitimas", LEVELS, ("2024M01",), (),
    time_grains=("mes", "trimestre", "semestre", "ano"),
)  # fmt: skip
STOCK = IndicatorMeta(
    "ocupados", "Ocupados", "Pessoas", "additive", "ocupados", LEVELS, ("2024T1",), (),
    time_grains=("trimestre",),
)  # fmt: skip
META = {"vitimas": FLOW, "ocupados": STOCK}


def test_grain_plan_is_derived() -> None:
    plan = plan_query(IndicatorQuery(("vitimas",), "uf", grain="trimestre"), META)
    assert plan.derived
    assert "per" in plan.aliases
    assert plan.params["grain"] == "trimestre"
    assert "somados" in plan.warnings[0]
    # O grão publicado devolve os valores publicados, sem agregação.
    same = plan_query(IndicatorQuery(("vitimas",), "uf", grain="mes"), META)
    assert not same.derived
    assert "per" not in same.aliases


@pytest.mark.parametrize(
    ("query", "message"),
    [
        (IndicatorQuery(("ocupados",), "uf", grain="ano"), "não pode ser detalhado por ano"),
        (IndicatorQuery(("vitimas",), "uf", grain="decada"), "grão de tempo inválido"),
        (
            IndicatorQuery(("vitimas",), "uf", grain="ano", sum_to="brasil"),
            "territórios e períodos",
        ),
    ],
)
def test_grain_rejections(query: IndicatorQuery, message: str) -> None:
    with pytest.raises(SemanticError, match=message):
        plan_query(query, META)


def test_grain_sql_sums_complete_periods_only() -> None:
    """O SQL gerado, executado no DuckDB com tabelas mínimas."""
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE obs AS SELECT * FROM (VALUES "
        "('vitimas','uf:29','uf','2025M01','none',1.0,'valid','Vítimas',[]::VARCHAR[],'t1'),"
        "('vitimas','uf:29','uf','2025M02','none',2.0,'valid','Vítimas',[]::VARCHAR[],'t1'),"
        "('vitimas','uf:29','uf','2025M03','none',0.0,'true_zero','Vítimas',[]::VARCHAR[],'t1'),"
        "('vitimas','uf:29','uf','2025M04','none',5.0,'valid','Vítimas',[]::VARCHAR[],'t1'),"
        "('vitimas','uf:29','uf','2025M05','none',NULL,'not_available','Vítimas',[]::VARCHAR[],'t1')"
        ") AS t(indicator_id, geography_key, level_id, period, breakdown_key, value, "
        "value_status, unit, flags, source_table_id)"
    )
    con.execute("CREATE TABLE geo AS SELECT 'uf:29' AS geography_key, 'Bahia' AS name")
    con.execute(
        "CREATE TABLE brk AS SELECT 'none' AS breakdown_key, 'Total' AS label, "
        "[]::VARCHAR[] AS non_total_classifications, []::VARCHAR[] AS category_keys"
    )
    con.execute(
        "CREATE TABLE per AS SELECT * FROM (VALUES "
        "('2025M01','2025T1','trimestre',3),('2025M02','2025T1','trimestre',3),"
        "('2025M03','2025T1','trimestre',3),('2025M04','2025T2','trimestre',3),"
        "('2025M05','2025T2','trimestre',3)) AS t(period, ancestor_period, ancestor_type, parts)"
    )
    plan = plan_query(IndicatorQuery(("vitimas",), "uf", grain="trimestre"), META)
    sql = plan.sql_template
    for alias in plan.aliases:
        sql = sql.replace("{{" + alias + "}}", alias)
    rows = con.execute(sql, dict(plan.params)).fetchall()
    cols = [d[0] for d in con.description]
    got = {r[cols.index("period")]: r for r in rows}
    t1, t2 = got["2025T1"], got["2025T2"]
    assert (t1[cols.index("value")], t1[cols.index("value_status")]) == (3.0, "derived_sum")
    # Abril publicado, maio indisponível e junho ausente: o trimestre fica sem valor.
    assert (t2[cols.index("value")], t2[cols.index("value_status")]) == (None, "incomplete_period")
    assert (t2[cols.index("parts_with_value")], t2[cols.index("parts_expected")]) == (1, 3)


@pytest.mark.parametrize(
    ("rule", "value", "status"),
    [("sum", 3.0, "derived_sum"), ("mean", 1.0, "derived_mean"), ("last", 0.0, "derived_last")],
)
def test_time_aggregation_rules(rule: str, value: float, status: str) -> None:
    """ADR-0017: soma (fluxos), média (números-índice) e último valor (acumulados)."""
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE obs AS SELECT * FROM (VALUES "
        "('x','uf:29','uf','2025M01','none',1.0,'valid','u',[]::VARCHAR[],'t1'),"
        "('x','uf:29','uf','2025M02','none',2.0,'valid','u',[]::VARCHAR[],'t1'),"
        "('x','uf:29','uf','2025M03','none',0.0,'true_zero','u',[]::VARCHAR[],'t1')"
        ") AS t(indicator_id, geography_key, level_id, period, breakdown_key, value, "
        "value_status, unit, flags, source_table_id)"
    )
    con.execute("CREATE TABLE geo AS SELECT 'uf:29' AS geography_key, 'Bahia' AS name")
    con.execute(
        "CREATE TABLE brk AS SELECT 'none' AS breakdown_key, 'Total' AS label, "
        "[]::VARCHAR[] AS non_total_classifications, []::VARCHAR[] AS category_keys"
    )
    con.execute(
        "CREATE TABLE per AS SELECT * FROM (VALUES "
        "('2025M01','2025T1','trimestre',3),('2025M02','2025T1','trimestre',3),"
        "('2025M03','2025T1','trimestre',3)) AS t(period, ancestor_period, ancestor_type, parts)"
    )
    meta = {
        "x": IndicatorMeta(
            "x",
            "X",
            "u",
            "non_additive",
            "x",
            LEVELS,
            ("2025M01",),
            (),
            time_grains=("mes", "trimestre", "semestre", "ano"),
            time_aggregation=rule,
        )
    }
    plan = plan_query(IndicatorQuery(("x",), "uf", grain="trimestre"), meta)
    sql = plan.sql_template
    for alias in plan.aliases:
        sql = sql.replace("{{" + alias + "}}", alias)
    row = con.execute(sql, dict(plan.params)).fetchone()
    cols = [d[0] for d in con.description]
    assert row is not None
    assert (row[cols.index("value")], row[cols.index("value_status")]) == (value, status)


def test_mixed_time_aggregations_are_refused() -> None:
    other = IndicatorMeta(
        "idx", "Índice", "Número-índice", "non_additive", "idx", LEVELS, ("2024M01",), (),
        time_grains=("mes", "trimestre", "semestre", "ano"), time_aggregation="mean",
    )  # fmt: skip
    meta = {**META, "idx": other}
    with pytest.raises(SemanticError, match="agregações no tempo diferentes"):
        plan_query(IndicatorQuery(("vitimas", "idx"), "uf", grain="ano"), meta)
