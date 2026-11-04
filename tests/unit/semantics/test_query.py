import pytest

from odb_semantics import (
    IndicatorMeta,
    IndicatorQuery,
    SemanticError,
    geography_key,
    level_rank,
    meta_from_rows,
    plan_query,
)

LEVELS = ("brasil", "regiao", "uf", "municipio")
META = {
    "pessoas": IndicatorMeta(
        "pessoas",
        "Pessoas",
        "Pessoas",
        "additive",
        "pessoas",
        LEVELS,
        ("2022",),
        ("c1", "c2"),
        ("cuidado com a soma",),
        {"cor": "definições diferentes"},
    ),
    "cor": IndicatorMeta(
        "cor",
        "Cor",
        "Pessoas",
        "additive",
        "populacao",
        LEVELS,
        ("2010", "2022"),
        ("c86",),
        incompatible_with={"pessoas": "definições diferentes"},
    ),
    "pct": IndicatorMeta("pct", "Pct", "%", "non_additive", "pct", LEVELS[:3], ("2022",), ()),
}


def test_levels() -> None:
    assert level_rank("brasil") == 1
    assert level_rank("municipio") == 6
    assert geography_key("uf", "29") == "uf:29"
    with pytest.raises(ValueError, match="desconhecido"):
        level_rank("distrito")


def test_basic_plan_keeps_unrequested_classifications_at_total() -> None:
    plan = plan_query(
        IndicatorQuery(
            ("pessoas",),
            "uf",
            within="regiao:2",
            periods=("2022",),
            breakdown={"c1": ("10", "11"), "c2": None},
        ),
        META,
    )
    assert set(plan.aliases) == {"obs", "geo", "brk", "anc"}
    assert plan.params["dims"] == ["c1", "c2"]
    assert plan.params["cats_0"] == ["c1:10", "c1:11"]
    assert "cats_1" not in plan.params
    assert plan.params["within"] == "regiao:2"
    assert "list_has_all" in plan.sql_template
    assert not plan.derived
    assert plan.warnings == ("pessoas: cuidado com a soma",)

    simple = plan_query(IndicatorQuery(("pct",), "brasil"), META)
    assert set(simple.aliases) == {"obs", "geo", "brk"}
    assert simple.params["dims"] == []


def test_sum_plan_is_derived() -> None:
    plan = plan_query(IndicatorQuery(("cor",), "municipio", sum_to="uf"), META)
    assert plan.derived
    assert plan.params["sum_to"] == "uf"
    assert "sum(o.value)" in plan.sql_template
    assert "derivado" in plan.warnings[0]


@pytest.mark.parametrize(
    ("query", "message"),
    [
        (IndicatorQuery((), "uf"), "ao menos um indicador"),
        (IndicatorQuery(("x",), "uf"), "não publicados"),
        (IndicatorQuery(("pessoas", "cor"), "uf"), "definições diferentes"),
        (IndicatorQuery(("pct",), "municipio"), "níveis disponíveis"),
        (IndicatorQuery(("cor",), "uf", breakdown={"c1": None}), "não tem as classificações"),
        (IndicatorQuery(("pct",), "uf", sum_to="brasil"), "não aditivos"),
        (IndicatorQuery(("cor",), "uf", sum_to="municipio"), "nível que contém"),
        (IndicatorQuery(("cor",), "uf", within="municipio:2927408"), "não contém unidades"),
        (IndicatorQuery(("cor",), "distrito"), "desconhecido"),
        (IndicatorQuery(("cor",), "uf", within="uf;drop"), "recorte territorial inválido"),
        (IndicatorQuery(("cor",), "uf", periods=("2022'",)), "períodos inválidos"),
        (IndicatorQuery(("cor",), "uf", breakdown={"c86": ("1 OR 1",)}), "categorias inválidas"),
        (IndicatorQuery(("cor",), "uf", breakdown={"c86": ()}), "categorias inválidas"),
    ],
)
def test_semantic_rejections(query: IndicatorQuery, message: str) -> None:
    with pytest.raises(SemanticError, match=message):
        plan_query(query, META)


def test_meta_from_rows() -> None:
    meta = meta_from_rows(
        [
            {
                "indicator_id": "a",
                "name": "A",
                "unit": "Pessoas",
                "additivity": "additive",
                "concept": "c",
                "available_levels": ["uf"],
                "periods": ["2022"],
                "classification_ids": None,
                "caveats": None,
                "incompatible_with": [{"indicator": "b", "reason": "r"}],
            }
        ]
    )
    assert meta["a"].incompatible_with == {"b": "r"}
    assert meta["a"].classification_ids == ()


def test_special_levels_use_ancestor_graph() -> None:
    tq_levels = ("brasil", "uf", "territorio_quilombola", "territorio_quilombola_uf")
    meta = {"tq": IndicatorMeta("tq", "TQ", "Pessoas", "additive", "tq", tq_levels, ("2022",), ())}
    summed = plan_query(
        IndicatorQuery(("tq",), "territorio_quilombola_uf", sum_to="territorio_quilombola"), meta
    )
    assert summed.derived
    within_uf = plan_query(
        IndicatorQuery(("tq",), "territorio_quilombola_uf", within="uf:29"), meta
    )
    assert within_uf.params["within"] == "uf:29"
    with pytest.raises(SemanticError, match="não contém unidades"):
        plan_query(IndicatorQuery(("tq",), "territorio_quilombola", within="uf:29"), meta)
    with pytest.raises(SemanticError, match="nível que contém"):
        plan_query(IndicatorQuery(("tq",), "territorio_quilombola", sum_to="uf"), meta)
