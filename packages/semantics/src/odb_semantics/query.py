"""Consultas semânticas sobre a Gold publicada (§15.4, §18.4).

O planejador recebe uma consulta estruturada (indicadores, nível territorial,
recorte, períodos, desagregações e agregação opcional), aplica as regras
semânticas e produz um template SQL com parâmetros nomeados para o
``ReadEngine``. As tabelas entram só como ``{{alias}}``, resolvidas pelo
manifesto do release vigente. Nada do usuário vira SQL.

Regras aplicadas:

1. indicadores existem no release consultado;
2. indicadores declarados incompatíveis não são combinados na mesma consulta
   (por exemplo, as duas definições de população indígena);
3. o nível pedido está entre os níveis publicados do indicador;
4. só se desagrega por classificações do indicador. Classificações não pedidas
   ficam no Total, o que impede misturar totais e categorias;
5. ``sum_to`` (soma dos territórios filhos até um nível superior) só vale para
   indicadores aditivos. O resultado é marcado como derivado, nunca oficial,
   e traz os alertas do indicador.
6. ``grain`` (trimestre, semestre ou ano a partir dos meses, ADR-0013) só vale para
   fluxos (``time_aggregation = "sum"``). O período maior é a soma das partes e só
   tem valor quando todas as partes têm valor; senão fica ``incomplete_period``,
   sem valor. Também é derivado, e não se combina com ``sum_to``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from odb_semantics.geography import is_ancestor_level, level_rank
from odb_semantics.periods import GRAIN_LABELS, GRAINS

_GEOGRAPHY_KEY = re.compile(r"^[a-z_]{2,32}:[0-9A-Za-z]{1,16}$")
_PERIOD = re.compile(r"^[0-9A-Za-z]{1,16}$")
_CATEGORY = re.compile(r"^[0-9A-Za-z_\-]{1,32}$")

# Aliases das tabelas Gold usadas pelo planejador (``table_id`` no release).
OBSERVATION_TABLE = "indicator_observation"
GEOGRAPHY_TABLE = "dim_geography"
ANCESTOR_TABLE = "bridge_geography_ancestor"
BREAKDOWN_TABLE = "dim_breakdown"
PERIOD_BRIDGE_TABLE = "bridge_period_ancestor"
TABLE_ALIASES = {
    "obs": OBSERVATION_TABLE,
    "geo": GEOGRAPHY_TABLE,
    "anc": ANCESTOR_TABLE,
    "brk": BREAKDOWN_TABLE,
    "per": PERIOD_BRIDGE_TABLE,
}


class SemanticError(ValueError):
    """Consulta rejeitada por regra semântica."""


@dataclass(frozen=True, slots=True)
class IndicatorMeta:
    """Metadados de um indicador no release (lidos de ``dim_indicator``)."""

    indicator_id: str
    name: str
    unit: str
    additivity: str
    concept: str
    available_levels: tuple[str, ...]
    periods: tuple[str, ...]
    classification_ids: tuple[str, ...]
    caveats: tuple[str, ...] = ()
    incompatible_with: Mapping[str, str] = field(default_factory=dict)
    # Grãos de tempo oferecidos, do publicado ao menos detalhado (ADR-0013).
    time_grains: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IndicatorQuery:
    """Consulta estruturada.

    ``breakdown`` mapeia classificação → categorias oficiais pedidas. ``None``
    traz todas as categorias, inclusive o Total.
    """

    indicators: tuple[str, ...]
    level: str
    within: str | None = None
    periods: tuple[str, ...] = ()
    breakdown: Mapping[str, tuple[str, ...] | None] = field(default_factory=dict)
    sum_to: str | None = None
    # Grão de tempo pedido; ``None`` ou o grão publicado devolvem os valores publicados.
    grain: str | None = None


@dataclass(frozen=True, slots=True)
class QueryPlan:
    """SQL controlado, parâmetros e metadados semânticos do resultado."""

    sql_template: str
    params: Mapping[str, Any]
    aliases: Mapping[str, str]
    warnings: tuple[str, ...]
    derived: bool


def _validate_shape(query: IndicatorQuery) -> None:
    if not query.indicators:
        msg = "informe ao menos um indicador"
        raise SemanticError(msg)
    if query.within is not None and not _GEOGRAPHY_KEY.fullmatch(query.within):
        msg = f"recorte territorial inválido: {query.within!r} (formato nível:código)"
        raise SemanticError(msg)
    try:
        level_rank(query.level)
        if query.sum_to is not None:
            level_rank(query.sum_to)
        if query.within is not None:
            level_rank(query.within.split(":", 1)[0])
    except ValueError as exc:
        raise SemanticError(str(exc)) from exc
    if query.grain is not None and query.grain not in GRAINS:
        msg = f"grão de tempo inválido: {query.grain!r} (use {list(GRAINS)})"
        raise SemanticError(msg)
    bad_periods = [p for p in query.periods if not _PERIOD.fullmatch(p)]
    if bad_periods:
        msg = f"períodos inválidos: {bad_periods}"
        raise SemanticError(msg)
    for cid, cats in query.breakdown.items():
        if cats is not None and (not cats or any(not _CATEGORY.fullmatch(c) for c in cats)):
            msg = f"categorias inválidas para {cid}: {cats}"
            raise SemanticError(msg)


def check_semantics(query: IndicatorQuery, meta: Mapping[str, IndicatorMeta]) -> list[str]:
    """Aplica as regras semânticas. Devolve os alertas do resultado."""
    _validate_shape(query)
    missing = [i for i in query.indicators if i not in meta]
    if missing:
        msg = f"indicadores não publicados no release: {missing}"
        raise SemanticError(msg)
    selected = [meta[i] for i in dict.fromkeys(query.indicators)]
    for a in selected:
        for b in selected:
            reason = a.incompatible_with.get(b.indicator_id)
            if reason:
                msg = f"{a.indicator_id} e {b.indicator_id} não podem ser combinados: {reason}"
                raise SemanticError(msg)
    for ind in selected:
        if query.level not in ind.available_levels:
            msg = (
                f"{ind.indicator_id} não é publicado no nível {query.level!r} "
                f"(níveis disponíveis: {list(ind.available_levels)})"
            )
            raise SemanticError(msg)
        unknown = sorted(set(query.breakdown) - set(ind.classification_ids))
        if unknown:
            msg = (
                f"{ind.indicator_id} não tem as classificações {unknown} "
                f"(disponíveis: {list(ind.classification_ids)})"
            )
            raise SemanticError(msg)
    warnings = [f"{ind.indicator_id}: {c}" for ind in selected for c in ind.caveats]
    if aggregates_time(query, meta):
        warnings.insert(0, _check_time(query, selected))
    if query.within is not None:
        within_level = query.within.split(":", 1)[0]
        if within_level != query.level and not is_ancestor_level(within_level, query.level):
            msg = f"o recorte {query.within} não contém unidades do nível {query.level}"
            raise SemanticError(msg)
    if query.sum_to is not None:
        warnings.insert(0, _check_sum_to(query, selected))
    return warnings


def _check_sum_to(query: IndicatorQuery, selected: Sequence[IndicatorMeta]) -> str:
    """Regra 5: soma territorial só de indicadores aditivos. Devolve o alerta."""
    if not is_ancestor_level(str(query.sum_to), query.level):
        msg = f"sum_to={query.sum_to} precisa ser um nível que contém {query.level}"
        raise SemanticError(msg)
    not_additive = [i.indicator_id for i in selected if i.additivity != "additive"]
    if not_additive:
        msg = (
            f"indicadores não aditivos não podem ser somados: {not_additive} "
            "(razões, percentuais e densidades)"
        )
        raise SemanticError(msg)
    return (
        f"valores somados a partir do nível {query.level}: resultado derivado, não é o "
        "total oficial. Para níveis publicados, consulte o valor oficial do próprio nível."
    )


def _check_time(query: IndicatorQuery, selected: Sequence[IndicatorMeta]) -> str:
    """Regra 6: o grão pedido vale para todos os indicadores. Devolve o alerta."""
    label = GRAIN_LABELS[str(query.grain)].lower()
    if query.sum_to is not None:
        msg = "não é possível somar territórios e períodos na mesma consulta"
        raise SemanticError(msg)
    for ind in selected:
        if query.grain not in ind.time_grains:
            msg = (
                f"{ind.indicator_id} não pode ser detalhado por {label} "
                f"(disponível: {list(ind.time_grains)})"
            )
            raise SemanticError(msg)
    return (
        f"valores por {label} somados a partir dos períodos publicados: resultado "
        "derivado. Período incompleto fica sem valor."
    )


def aggregates_time(query: IndicatorQuery, meta: Mapping[str, IndicatorMeta]) -> bool:
    """A consulta pede um grão de tempo maior que o publicado."""
    if query.grain is None:
        return False
    published = {
        meta[i].time_grains[0] for i in query.indicators if i in meta and meta[i].time_grains
    }
    return published != {query.grain}


def _filters(
    query: IndicatorQuery, params: dict[str, Any], period_column: str = "o.period"
) -> list[str]:
    where = [
        "list_contains(CAST($indicators AS VARCHAR[]), o.indicator_id)",
        "o.level_id = $level",
        # Classificações não pedidas ficam no Total.
        "list_has_all(CAST($dims AS VARCHAR[]), b.non_total_classifications)",
    ]
    params.update(
        indicators=list(dict.fromkeys(query.indicators)),
        level=query.level,
        dims=sorted(query.breakdown),
    )
    if query.periods:
        where.append(f"list_contains(CAST($periods AS VARCHAR[]), {period_column})")
        params["periods"] = list(query.periods)
    if query.within is not None:
        where.append(
            "EXISTS (SELECT 1 FROM {{anc}} AS w WHERE w.geography_key = o.geography_key "
            "AND w.ancestor_key = $within)"
        )
        params["within"] = query.within
    for n, (cid, cats) in enumerate(sorted(query.breakdown.items())):
        if cats is None:
            continue
        name = f"cats_{n}"
        where.append(f"list_has_any(b.category_keys, CAST(${name} AS VARCHAR[]))")
        params[name] = [f"{cid}:{c}" for c in cats]
    return where


def plan_query(query: IndicatorQuery, meta: Mapping[str, IndicatorMeta]) -> QueryPlan:
    """Valida e monta o SQL da consulta."""
    warnings = check_semantics(query, meta)
    params: dict[str, Any] = {}
    by_time = aggregates_time(query, meta)
    where = " AND ".join(_filters(query, params, "p.ancestor_period" if by_time else "o.period"))
    order = "ORDER BY indicator_id, period, geography_key, breakdown_key"
    # O SQL é composto só de fragmentos fixos deste módulo; valores entram como $parâmetros.
    if by_time:
        params["grain"] = query.grain
        complete = "count(o.value) = any_value(p.parts)"
        sql = (
            "SELECT o.indicator_id, o.geography_key, g.name AS territory_name, o.level_id, "
            "p.ancestor_period AS period, o.breakdown_key, b.label AS breakdown_label, "
            f"CASE WHEN {complete} THEN sum(o.value) END AS value, "
            f"CASE WHEN {complete} THEN 'derived_sum' ELSE 'incomplete_period' END "
            "AS value_status, any_value(o.unit) AS unit, count(o.value) AS parts_with_value, "
            "any_value(p.parts) AS parts_expected FROM {{obs}} AS o "
            "JOIN {{per}} AS p ON p.period = o.period AND p.ancestor_type = $grain "
            "JOIN {{geo}} AS g ON g.geography_key = o.geography_key "
            "JOIN {{brk}} AS b ON b.breakdown_key = o.breakdown_key "
            f"WHERE {where} "
            "GROUP BY o.indicator_id, o.geography_key, g.name, o.level_id, p.ancestor_period, "
            f"o.breakdown_key, b.label {order}"
        )
        aliases = {a: TABLE_ALIASES[a] for a in ("obs", "geo", "brk", "per")}
    elif query.sum_to is None:
        sql = (
            "SELECT o.indicator_id, o.geography_key, g.name AS territory_name, o.level_id, "
            "o.period, o.breakdown_key, b.label AS breakdown_label, o.value, o.value_status, "
            "o.unit FROM {{obs}} AS o "
            "JOIN {{geo}} AS g ON g.geography_key = o.geography_key "
            "JOIN {{brk}} AS b ON b.breakdown_key = o.breakdown_key "
            f"WHERE {where} {order}"
        )
        aliases = {a: TABLE_ALIASES[a] for a in ("obs", "geo", "brk")}
    else:
        params["sum_to"] = query.sum_to
        sql = (
            "SELECT o.indicator_id, a.ancestor_key AS geography_key, g.name AS territory_name, "
            "a.ancestor_level AS level_id, o.period, o.breakdown_key, "
            "b.label AS breakdown_label, sum(o.value) AS value, "
            "CASE WHEN count(*) > count(o.value) THEN 'incomplete_sum' ELSE 'derived_sum' END "
            "AS value_status, any_value(o.unit) AS unit, count(*) AS children, "
            "count(o.value) AS children_with_value, "
            "count(*) FILTER (WHERE list_contains(o.flags, 'pending_installation')) "
            "AS children_pending_installation FROM {{obs}} AS o "
            "JOIN {{anc}} AS a ON a.geography_key = o.geography_key "
            "AND a.ancestor_level = $sum_to "
            "JOIN {{geo}} AS g ON g.geography_key = a.ancestor_key "
            "JOIN {{brk}} AS b ON b.breakdown_key = o.breakdown_key "
            f"WHERE {where} "
            "GROUP BY o.indicator_id, a.ancestor_key, g.name, a.ancestor_level, o.period, "
            f"o.breakdown_key, b.label {order}"
        )
        aliases = {a: TABLE_ALIASES[a] for a in ("obs", "geo", "brk", "anc")}
    if query.within is not None:
        aliases["anc"] = ANCESTOR_TABLE
    return QueryPlan(
        sql_template=sql,
        params=params,
        aliases=aliases,
        warnings=tuple(warnings),
        derived=query.sum_to is not None or by_time,
    )


def meta_from_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, IndicatorMeta]:
    """``IndicatorMeta`` a partir das linhas de ``dim_indicator``."""
    out: dict[str, IndicatorMeta] = {}
    for r in rows:
        out[str(r["indicator_id"])] = IndicatorMeta(
            indicator_id=str(r["indicator_id"]),
            name=str(r["name"]),
            unit=str(r["unit"]),
            additivity=str(r["additivity"]),
            concept=str(r["concept"]),
            available_levels=tuple(r["available_levels"] or ()),
            periods=tuple(r["periods"] or ()),
            classification_ids=tuple(r["classification_ids"] or ()),
            caveats=tuple(r["caveats"] or ()),
            incompatible_with={
                str(i["indicator"]): str(i["reason"]) for i in r["incompatible_with"] or ()
            },
            time_grains=tuple(r.get("time_grains") or ()),
        )
    return out
