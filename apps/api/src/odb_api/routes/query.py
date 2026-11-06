"""Consulta estruturada (sem SQL) sobre qualquer indicador publicado."""

from __future__ import annotations

from fastapi import APIRouter

from odb_api.kpis import provenance, to_float
from odb_api.routes.common import ERRORS, Ctx, Deps
from odb_api.schemas import QueryIn, QueryOut, QueryRowOut
from odb_semantics import IndicatorQuery, check_semantics, plan_query

router = APIRouter(prefix="/api/v1", tags=["consulta"], responses=ERRORS)


@router.post("/query", response_model=QueryOut, summary="Consulta de indicadores")
def query(d: Deps, ctx: Ctx, body: QueryIn) -> QueryOut:
    """Indicadores x território x período x desagregação, com as regras semânticas.

    ``breakdown`` mapeia classificação → categorias (``null`` traz todas). As
    classificações não pedidas ficam no Total. ``sum_to`` soma os territórios
    até um nível superior e marca o resultado como derivado.
    """
    limit = min(body.limit, d.settings.page_max)
    request = IndicatorQuery(
        indicators=tuple(body.indicators),
        level=body.level,
        within=body.within,
        periods=tuple(body.periods),
        breakdown={k: None if v is None else tuple(v) for k, v in body.breakdown.items()},
        sum_to=body.sum_to,
    )
    meta = d.gold.indicator_meta(ctx)
    warnings = check_semantics(request, meta)
    plan = plan_query(request, meta)
    result = d.gold.run_plan(ctx, plan, max_rows=body.offset + limit + 1)
    rows = [dict(zip(result.columns, r, strict=True)) for r in result.rows]
    page = rows[body.offset : body.offset + limit]
    has_more = len(rows) > body.offset + limit
    return QueryOut(
        rows=[
            QueryRowOut(
                indicator_id=r["indicator_id"],
                geography_key=r["geography_key"],
                territory_name=r["territory_name"],
                level_id=r["level_id"],
                period=r["period"],
                breakdown_key=r["breakdown_key"],
                breakdown_label=r["breakdown_label"] or "Total",
                value=to_float(r["value"]),
                value_status=r["value_status"],
                unit=r["unit"],
            )
            for r in page
        ],
        has_more=has_more,
        offset=body.offset,
        limit=limit,
        warnings=warnings,
        provenance=provenance(ctx, plan.aliases.values(), derived=plan.derived, truncated=has_more),
    )
