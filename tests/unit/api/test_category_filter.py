"""Filtro de categorias do "Detalhar por" (DS 2.4): Total = soma das escolhidas."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from odb_api.kpis import Observation, filter_totals


def _o(combo: tuple[str, ...], value: float | None, status: str = "valid") -> Observation:
    return Observation(
        geography_key="uf:51",
        name="Mato Grosso",
        period="2025",
        combo=combo,
        value=None if value is None else Decimal(str(value)),
        status=status,
    )


TOTALS = {"c79": "c79:T", "c2": "c2:T"}


def test_total_becomes_sum_of_selected() -> None:
    obs = [_o(("c79:T",), 100), _o(("c79:bov",), 60), _o(("c79:cap",), 10)]
    out = filter_totals(obs, ["c79"], {"c79": frozenset({"c79:bov", "c79:cap"})}, TOTALS)
    total = next(o for o in out if o.combo == ("c79:T",))
    assert total.value == Decimal(70)
    assert total.status == "derived_sum"


def test_not_surveyed_parts_are_skipped_and_suppressed_blocks() -> None:
    chosen = {"c79": frozenset({"c79:bov", "c79:cap"})}
    skipped = filter_totals(
        [_o(("c79:T",), 100), _o(("c79:bov",), 60), _o(("c79:cap",), None, "not_available")],
        ["c79"],
        chosen,
        TOTALS,
    )
    assert skipped[0].value == Decimal(60)
    blocked = filter_totals(
        [_o(("c79:T",), 100), _o(("c79:bov",), 60), _o(("c79:cap",), None, "suppressed")],
        ["c79"],
        chosen,
        TOTALS,
    )
    assert blocked[0].value is None
    assert blocked[0].status == "suppressed"


def test_crossed_dimensions_sum_both_filters() -> None:
    # Tipo x sexo: o Total geral soma só as células escolhidas nas duas dimensões.
    obs = [
        _o(("c79:T", "c2:T"), 100),
        _o(("c79:a", "c2:T"), 70),
        _o(("c79:b", "c2:T"), 30),
        _o(("c79:T", "c2:m"), 50),
        _o(("c79:a", "c2:m"), 40),
        _o(("c79:b", "c2:m"), 10),
    ]
    chosen = {"c79": frozenset({"c79:a"}), "c2": frozenset({"c2:m"})}
    out = {o.combo: o.value for o in filter_totals(obs, ["c79", "c2"], chosen, TOTALS)}
    assert out[("c79:T", "c2:T")] == Decimal(40)  # só a e m
    assert out[("c79:a", "c2:T")] == Decimal(40)
    assert out[("c79:T", "c2:m")] == Decimal(40)


def test_filtro_preserva_a_identificacao_da_soma_regional_parcial() -> None:
    obs = [_o(("c79:T",), 100), _o(("c79:bov",), 60, "partial_sum"), _o(("c79:cap",), 10)]
    out = filter_totals(obs, ["c79"], {"c79": frozenset({"c79:bov", "c79:cap"})}, TOTALS)
    assert out[0].value == Decimal(70)
    assert out[0].status == "partial_sum"


def test_detalhe_regional_ausente_nao_esconde_outra_categoria_disponivel() -> None:
    obs = [
        replace(o, geography_key="regiao:1", name="Norte")
        for o in [
            _o(("c79:T",), 100, "derived_sum"),
            _o(("c79:bov",), 60, "derived_sum"),
            _o(("c79:cap",), None, "suppressed"),
        ]
    ]
    out = filter_totals(obs, ["c79"], {"c79": frozenset({"c79:bov", "c79:cap"})}, TOTALS)
    assert out[0].value == Decimal(60)
    assert out[0].status == "partial_sum"
