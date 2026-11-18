"""Portal: navegação e KPIs (mapa, detalhe, série, tabela) e exportação."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request
from fastapi.responses import Response

from odb_api import exports
from odb_api.routes.common import ERRORS, GEOGRAPHY_KEY, ID, PERIOD, Cats, Ctx, Deps, Dims, Periods
from odb_api.schemas import (
    DetailOut,
    ErrorOut,
    ExportIn,
    Grain,
    HistoryOut,
    KpiOut,
    MapOut,
    NavigationOut,
    PivotOut,
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
AccumulateQ = Annotated[
    bool, Query(description="Acumulado dos períodos em ``periods`` (só fluxos e variações %).")
]
CorrectionQ = Annotated[
    str | None,
    Query(
        pattern=r"^[a-z][a-z0-9_]{0,31}$",
        description="Correção por índice de preços (ADR-0020), ex.: ipca, ipca_grupo.",
    ),
]


def _cached_json(request: Request, release_id: str, key: str, body: bytes) -> Response:
    """JSON pronto do release, com ETag (304 quando o cliente já o tem)."""
    etag = f'"{release_id}:{key}"'
    headers = {"ETag": etag, "Cache-Control": "public, max-age=60", "X-ODB-Release": release_id}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)


@router.get("/portal/navigation", response_model=NavigationOut, summary="Navegação do portal")
def navigation(request: Request, d: Deps, ctx: Ctx) -> Response:
    """Temas, subtemas e KPIs, com níveis, períodos e dimensões disponíveis."""
    body, _ = d.kpis.serialized(ctx)
    return _cached_json(request, ctx.release_id, "navigation", body)


@router.get("/kpis/{kpi_id}", response_model=KpiOut, summary="KPI")
def kpi(request: Request, d: Deps, ctx: Ctx, kpi_id: KpiId) -> Response:
    """Metadados de um KPI."""
    _, kpis = d.kpis.serialized(ctx)
    body = kpis.get(kpi_id)
    if body is None:
        d.kpis.kpi(ctx, kpi_id)  # levanta 404
        raise AssertionError  # pragma: no cover
    return _cached_json(request, ctx.release_id, f"kpi:{kpi_id}", body)


@router.get("/kpis/{kpi_id}/map", response_model=MapOut, summary="Valores para o mapa")
def kpi_map(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    level: Level,
    cats: Cats,
    periods: Periods,
    period: Period = None,
    within: Within = None,
    grain: GrainQ = None,
    correction: CorrectionQ = None,
    accumulate: AccumulateQ = False,
) -> MapOut:
    """Total do KPI em cada território do nível (ou a soma das categorias filtradas)."""
    return d.kpis.map(
        ctx,
        kpi_id,
        level=level,
        period=period,
        within=within,
        grain=grain,
        correction=correction,
        categories=cats,
        periods=periods,
        accumulate=accumulate,
    )


@router.get("/kpis/{kpi_id}/detail", response_model=DetailOut, summary="Detalhe (tooltip)")
def kpi_detail(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    geography: Geography,
    dims: Dims,
    cats: Cats,
    periods: Periods,
    period: Period = None,
    grain: GrainQ = None,
    correction: CorrectionQ = None,
    accumulate: AccumulateQ = False,
) -> DetailOut:
    """Sub-KPIs aninhados de um território, na ordem das dimensões do portal."""
    return d.kpis.detail(
        ctx,
        kpi_id,
        geography=geography,
        period=period,
        dimensions=dims,
        grain=grain,
        correction=correction,
        categories=cats,
        periods=periods,
        accumulate=accumulate,
    )


@router.get("/kpis/{kpi_id}/series", response_model=SeriesOut, summary="Série temporal")
def kpi_series(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    geography: Geography,
    dims: Dims,
    cats: Cats,
    periods: Periods,
    grain: GrainQ = None,
    correction: CorrectionQ = None,
    accumulate: Annotated[
        Literal["running", "year"] | None,
        Query(description="Acumulado corrente (running) ou no ano (year), ADR-0026."),
    ] = None,
) -> SeriesOut:
    """Todos os períodos publicados de um território (ou somados no grão pedido)."""
    return d.kpis.series(
        ctx,
        kpi_id,
        geography=geography,
        dimensions=dims,
        grain=grain,
        correction=correction,
        categories=cats,
        periods=periods,
        accumulate=accumulate,
    )


@router.get("/kpis/{kpi_id}/table", response_model=TableOut, summary="Tabela")
def kpi_table(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    level: Level,
    dims: Dims,
    cats: Cats,
    periods: Periods,
    period: Period = None,
    within: Within = None,
    accumulate: Annotated[
        Literal["total", "running", "year"] | None,
        Query(description="Acumulado: total (uma coluna), running ou year, ADR-0026."),
    ] = None,
    sort: Annotated[Literal["value", "name"], Query()] = "value",
    order: Annotated[Literal["asc", "desc"], Query()] = "desc",
    grain: GrainQ = None,
    correction: CorrectionQ = None,
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
        correction=correction,
        categories=cats,
        periods=periods,
        accumulate=accumulate,
    )


@router.get(
    "/kpis/{kpi_id}/history", response_model=HistoryOut, summary="Série completa de um território"
)
def kpi_history(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    geography: Geography,
    dims: Dims,
    cats: Cats,
    grains: Annotated[
        str | None,
        Query(
            pattern=r"^(mes|trimestre|semestre|ano)(,(mes|trimestre|semestre|ano)){0,3}$",
            description="Grãos de tempo separados por vírgula; padrão: todos os do KPI.",
        ),
    ] = None,
    correction: CorrectionQ = None,
) -> HistoryOut:
    """Todos os períodos de um território nos grãos pedidos, com os derivados marcados (B5)."""
    return d.kpis.history(
        ctx,
        kpi_id,
        geography=geography,
        dimensions=dims,
        grains=tuple(grains.split(",")) if grains else (),
        correction=correction,
        categories=cats,
    )


FIELDS = r"^[a-z][a-z0-9_]{0,31}(,[a-z][a-z0-9_]{0,31}){0,3}$"


@router.get("/kpis/{kpi_id}/pivot", response_model=PivotOut, summary="Tabela dinâmica")
def kpi_pivot(
    d: Deps,
    ctx: Ctx,
    kpi_id: KpiId,
    level: Level,
    cats: Cats,
    rows: Annotated[
        str, Query(pattern=FIELDS, description="Campos nas linhas: territorio, periodo, cNNN.")
    ],
    cols: Annotated[str, Query(pattern=FIELDS, description="Campos nas colunas.")],
    periods: Periods,
    within: Within = None,
    grain: GrainQ = None,
    correction: CorrectionQ = None,
) -> PivotOut:
    """Linhas e colunas à escolha; os campos fora delas ficam no Total publicado (B6).

    Com ``periods``, só esses períodos (DS 2.9: a tabela segue o Período do portal)."""
    return d.kpis.pivot(
        ctx,
        kpi_id,
        level=level,
        within=within,
        rows=rows.split(","),
        cols=cols.split(","),
        grain=grain,
        correction=correction,
        categories=cats,
        periods=periods,
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
    limit = exports.row_limit(body.kpi_id, d.settings.export_max_rows)
    levels = body.levels or [body.level]
    grains: list[str | None] = list(body.grains) or [body.grain]
    multi = len(levels) > 1 or len(grains) > 1 or bool(body.levels or body.grains)
    frames = []
    total = 0
    published = d.kpis.published_grain(ctx, body.kpi_id)
    cfg = d.kpis.kpi(ctx, body.kpi_id)
    for level in levels:
        # Dimensões marginais (ADR-0016) que não se cruzam neste nível: uma passada por
        # dimensão, no mesmo arquivo (as outras colunas de dimensão ficam vazias).
        crossable = (
            not cfg.exclusive_dimensions
            or len(body.dimensions) <= 1
            or cfg.can_cross(list(body.dimensions), level)
        )
        dim_sets = [list(body.dimensions)] if crossable else [[x] for x in body.dimensions]
        for grain, dim_set in ((g, ds) for g in grains for ds in dim_sets):
            kpi_cfg, dims, obs, prov = d.kpis.export_rows(
                ctx,
                body.kpi_id,
                level=level,
                periods=body.periods if not multi else [],
                within=body.within,
                dimensions=dim_set,
                max_rows=limit - total,
                grain=grain,
                correction=body.correction,
                categories=body.categories,
            )
            total += len(obs)
            # prov.truncated: o motor de consulta cortou o resultado no próprio teto
            # (duckdb_max_rows). Nunca entregar um arquivo incompleto como se fosse inteiro.
            if total > limit or prov.truncated:
                msg = (
                    f"a exportação passa do limite de {limit:,} linhas".replace(",", ".")
                    + "; desmarque níveis, grãos ou detalhes, ou recorte por um estado"
                )
                raise exports.ExportTooLargeError(msg)
            indicator = d.gold.indicators(ctx)[kpi_cfg.indicator]
            categories = d.gold.categories(ctx)
            labels = {dim.classification: dim.label for dim in kpi_cfg.dimensions}
            ufs = {
                g["geography_key"]: g["uf_abbreviation"]
                for g in d.gold.search_geographies(
                    ctx, text=None, levels=(level,), within=body.within, limit=50_000
                )
            }
            part = exports.frame(
                obs,
                dims=dims,
                labels=labels,
                category_names={k: c["name"] for k, c in categories.items()},
                ufs=ufs,
                unit=(
                    f"{indicator['unit']} a preços de {prov.price_base} ({prov.correction_label})"
                    if prov.correction
                    else indicator["unit"]
                ),
            )
            if multi:
                derived = grain is not None and grain != published
                part = exports.tag(
                    part,
                    level=level,
                    grain=grain or published or "publicado",
                    kind="derivado" if derived else "publicado",
                )
            frames.append(part)
    data = exports.concat(frames)
    found = d.catalog.datasets(indicator["dataset_id"])
    meta = exports.metadata(
        kpi={"kpi_id": kpi_cfg.id, "label": kpi_cfg.label},
        indicator=indicator,
        dataset=(
            {k: v for k, v in found[0].items() if k not in {"description"}} if found else None
        ),
        filters={
            "level": levels if multi else body.level,
            "grains": [g or "publicado" for g in grains] if multi else body.grain,
            "within": body.within,
            "periods": body.periods or "todos",
            "dimensions": dims,
            "correction": body.correction,
        },
        provenance=prov,
        rows=data.height,
    )
    content = exports.render(data, meta, body.format)
    where = "niveis" if len(levels) > 1 else levels[0]
    name = f"{kpi_cfg.id}_{where}.{exports.EXTENSIONS[body.format]}"
    return Response(
        content,
        media_type=exports.MEDIA_TYPES[body.format],
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "X-ODB-Release": ctx.release_id,
            # Lidos pelo log de acesso do Caddy para contar downloads (ADR-0027): o corpo
            # do POST não aparece no log.
            "X-ODB-KPI": kpi_cfg.id,
            "X-ODB-Format": body.format,
        },
    )
