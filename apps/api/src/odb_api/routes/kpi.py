"""Portal: navegação e KPIs (mapa, detalhe, série, tabela) e exportação."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query
from fastapi.responses import Response

from odb_api import exports
from odb_api.routes.common import ERRORS, GEOGRAPHY_KEY, ID, PERIOD, Ctx, Deps, Dims
from odb_api.schemas import (
    DetailOut,
    ErrorOut,
    ExportIn,
    Grain,
    KpiOut,
    MapOut,
    NavigationOut,
    SeriesOut,
    TableOut,
)

router = APIRouter(prefix="/api/v1", tags=["portal"], responses=ERRORS)
KpiId = Annotated[str, Path(pattern=ID)]
Level = Annotated[str, Query(pattern=ID, description="Nível territorial, ex.: uf.")]
Period = Annotated[str | None, Query(pattern=PERIOD, description="Padrão: o mais recente.")]
Within = Annotated[str | None, Query(pattern=GEOGRAPHY_KEY, description="Recorte, ex.: uf:29.")]
Geography = Annotated[str, Query(pattern=GEOGRAPHY_KEY, description="Território, ex.: uf:29.")]
GrainQ = Annotated[
    Grain | None,
    Query(description="Grão de tempo: soma os meses em trimestre, semestre ou ano (só fluxos)."),
]


@router.get("/portal/navigation", response_model=NavigationOut, summary="Navegação do portal")
def navigation(d: Deps, ctx: Ctx) -> NavigationOut:
    """Temas, subtemas e KPIs, com níveis, períodos e dimensões disponíveis."""
    return d.kpis.navigation(ctx)


@router.get("/kpis/{kpi_id}", response_model=KpiOut, summary="KPI")
def kpi(d: Deps, ctx: Ctx, kpi_id: KpiId) -> KpiOut:
    """Metadados de um KPI."""
    for theme in d.kpis.navigation(ctx).themes:
        for sub in theme.subthemes:
            for item in sub.kpis:
                if item.kpi_id == kpi_id:
                    return item
    d.kpis.kpi(ctx, kpi_id)  # levanta 404
    raise AssertionError  # pragma: no cover


@router.get("/kpis/{kpi_id}/map", response_model=MapOut, summary="Valores para o mapa")
def kpi_map(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    level: Level,
    period: Period = None,
    within: Within = None,
    grain: GrainQ = None,
) -> MapOut:
    """Total do KPI em cada território do nível."""
    return d.kpis.map(ctx, kpi_id, level=level, period=period, within=within, grain=grain)


@router.get("/kpis/{kpi_id}/detail", response_model=DetailOut, summary="Detalhe (tooltip)")
def kpi_detail(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    geography: Geography,
    dims: Dims,
    period: Period = None,
    grain: GrainQ = None,
) -> DetailOut:
    """Sub-KPIs aninhados de um território, na ordem das dimensões do portal."""
    return d.kpis.detail(
        ctx, kpi_id, geography=geography, period=period, dimensions=dims, grain=grain
    )


@router.get("/kpis/{kpi_id}/series", response_model=SeriesOut, summary="Série temporal")
def kpi_series(
    d: Deps, ctx: Ctx, kpi_id: KpiId, geography: Geography, dims: Dims, grain: GrainQ = None
) -> SeriesOut:
    """Todos os períodos publicados de um território (ou somados no grão pedido)."""
    return d.kpis.series(ctx, kpi_id, geography=geography, dimensions=dims, grain=grain)


@router.get("/kpis/{kpi_id}/table", response_model=TableOut, summary="Tabela")
def kpi_table(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    level: Level,
    dims: Dims,
    period: Period = None,
    within: Within = None,
    sort: Annotated[Literal["value", "name"], Query()] = "value",
    order: Annotated[Literal["asc", "desc"], Query()] = "desc",
    grain: GrainQ = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=10_000)] = 100,
    locate: Annotated[
        str | None,
        Query(
            pattern=GEOGRAPHY_KEY,
            description="Território a localizar: devolve a página que o contém (ignora offset).",
        ),
    ] = None,
) -> TableOut:
    """Territórios do nível com o Total e as combinações de categorias, paginados."""
    return d.kpis.table(
        ctx,
        kpi_id,
        level=level,
        period=period,
        within=within,
        dimensions=dims,
        sort=sort,
        descending=order == "desc",
        offset=offset,
        limit=limit,
        locate=locate,
        grain=grain,
    )


@router.post(
    "/exports",
    summary="Exportação de um KPI",
    response_class=Response,
    responses={
        200: {"content": {t: {} for t in exports.MEDIA_TYPES.values()}},
        413: {"model": ErrorOut, "description": "Exportação acima do limite de linhas"},
    },
)
def export(d: Deps, ctx: Ctx, body: ExportIn) -> Response:
    """CSV (ZIP com metadados), XLSX, Parquet ou JSON, sempre com metadados."""
    limit = d.settings.export_max_rows
    kpi_cfg, dims, obs, prov = d.kpis.export_rows(
        ctx,
        body.kpi_id,
        level=body.level,
        periods=body.periods,
        within=body.within,
        dimensions=body.dimensions,
        max_rows=limit,
        grain=body.grain,
    )
    if len(obs) > limit:
        msg = f"a exportação passa do limite de {limit} linhas; aplique filtros"
        raise exports.ExportTooLargeError(msg)
    indicator = d.gold.indicators(ctx)[kpi_cfg.indicator]
    categories = d.gold.categories(ctx)
    labels = {dim.classification: dim.label for dim in kpi_cfg.dimensions}
    ufs = {
        g["geography_key"]: g["uf_abbreviation"]
        for g in d.gold.search_geographies(
            ctx, text=None, levels=(body.level,), within=body.within, limit=50_000
        )
    }
    data = exports.frame(
        obs,
        dims=dims,
        labels=labels,
        category_names={k: c["name"] for k, c in categories.items()},
        ufs=ufs,
        unit=indicator["unit"],
    )
    found = d.catalog.datasets(indicator["dataset_id"])
    meta = exports.metadata(
        kpi={"kpi_id": kpi_cfg.id, "label": kpi_cfg.label},
        indicator=indicator,
        dataset=(
            {k: v for k, v in found[0].items() if k not in {"description"}} if found else None
        ),
        filters={
            "level": body.level,
            "within": body.within,
            "periods": body.periods or "todos",
            "dimensions": dims,
        },
        provenance=prov,
        rows=data.height,
    )
    content = exports.render(data, meta, body.format)
    name = f"{kpi_cfg.id}_{body.level}.{exports.EXTENSIONS[body.format]}"
    return Response(
        content,
        media_type=exports.MEDIA_TYPES[body.format],
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "X-ODB-Release": ctx.release_id,
        },
    )
