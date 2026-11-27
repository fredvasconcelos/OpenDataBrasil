"""Bloco 2 do portal: contas públicas federais (ADR-0034, ADR-0036, ADR-0037).

As rotas leem o release do escopo ``contas``, informado em ``X-ODB-Release``. Não
aceitam SQL, caminhos nem nomes de tabela: só parâmetros estruturados e validados.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response

from odb_api.contas import ContasService
from odb_api.contas_schemas import (
    ContasCompositionOut,
    ContasExecutionOut,
    ContasMapOut,
    ContasMetaOut,
    ContasRankingOut,
    ContasSearchOut,
    ContasSeriesOut,
    ContasTableOut,
    RecipientProfileOut,
)
from odb_api.release import ReleaseContext, ReleaseUnavailableError
from odb_api.routes.common import ERRORS, GEOGRAPHY_KEY, ID, Deps, Periods

router = APIRouter(prefix="/api/v1/contas", tags=["contas públicas"], responses=ERRORS)

LensQ = Annotated[Literal["A", "B"], Query(description="A: transferências; B: favorecidos.")]
GeoQ = Annotated[str, Query(pattern=GEOGRAPHY_KEY, description="Território, ex.: uf:25.")]
DimQ = Annotated[str | None, Query(pattern=ID, description="Dimensão do detalhar por.")]
PageQ = Annotated[int, Query(ge=1, le=100, description="Página de 10 linhas (até 100).")]


def _split(values: list[str] | None, limit: int) -> list[str]:
    out: list[str] = []
    for item in values or []:
        out.extend(p.strip() for p in item.split(",") if p.strip())
    return out[:limit]


def service(d: Deps) -> ContasService:
    """Serviço das contas (503 quando o bloco não está configurado)."""
    if d.contas is None:
        msg = "bloco de contas públicas indisponível nesta API"
        raise ReleaseUnavailableError(msg)
    return d.contas


def contas_context(
    response: Response, svc: Annotated[ContasService, Depends(service)]
) -> ReleaseContext:
    """Release do escopo ``contas`` da requisição (cabeçalho ``X-ODB-Release``)."""
    ctx = svc.resolver.current()
    response.headers["X-ODB-Release"] = ctx.release_id
    return ctx


Svc = Annotated[ContasService, Depends(service)]
CCtx = Annotated[ReleaseContext, Depends(contas_context)]


@router.get("/meta", response_model=ContasMetaOut, summary="Lentes, dimensões e meses")
def meta(svc: Svc, ctx: CCtx) -> ContasMetaOut:
    """O que o release oferece e a situação de cada mês (aberto, incompleto, fechado)."""
    return svc.meta(ctx)


@router.get("/map", response_model=ContasMapOut, summary="Mapa: total por território")
def contas_map(
    svc: Svc,
    ctx: CCtx,
    periods: Periods,
    lens: LensQ = "A",
    level: Annotated[Literal["regiao", "uf", "municipio"], Query()] = "uf",
    within: Annotated[str | None, Query(pattern=GEOGRAPHY_KEY)] = None,
    dimension: DimQ = None,
    categories: Annotated[
        list[str] | None, Query(description="Categorias da dimensão (soma das escolhidas).")
    ] = None,
) -> ContasMapOut:
    """Só o montante por território (ADR-0034, decisão 1); com ``dimension`` e
    ``categories``, a soma das categorias escolhidas."""
    return svc.map(
        ctx,
        lens=lens,
        level=level,
        within=within,
        periods=periods,
        dimension=dimension,
        categories=_split(categories, 50),
    )


@router.get("/composition", response_model=ContasCompositionOut, summary="Composição do território")
def composition(
    svc: Svc,
    ctx: CCtx,
    periods: Periods,
    geography_key: GeoQ,
    dimension: Annotated[str, Query(pattern=ID)],
    lens: LensQ = "A",
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> ContasCompositionOut:
    """As maiores categorias do território e "demais" (tooltip e gráfico de barras)."""
    return svc.composition(
        ctx, lens=lens, geography_key=geography_key, periods=periods, dimension=dimension,
        limit=limit,
    )  # fmt: skip


@router.get("/series", response_model=ContasSeriesOut, summary="Série mensal ou anual")
def series(
    svc: Svc,
    ctx: CCtx,
    periods: Periods,
    geography_key: GeoQ = "brasil:1",
    lens: LensQ = "A",
    grain: Annotated[Literal["mes", "ano"], Query()] = "mes",
    dimension: DimQ = None,
    categories: Annotated[list[str] | None, Query()] = None,
) -> ContasSeriesOut:
    """Total, ou até 10 categorias + "demais", no território (ADR-0034, decisão 2)."""
    return svc.series(
        ctx,
        lens=lens,
        geography_key=geography_key,
        periods=periods,
        grain=grain,
        dimension=dimension,
        categories=_split(categories, 10),
    )


@router.get("/ranking", response_model=ContasRankingOut, summary="Maiores destinatários")
def ranking(
    svc: Svc,
    ctx: CCtx,
    geography_key: GeoQ = "brasil:1",
    lens: LensQ = "B",
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    page: PageQ = 1,
) -> ContasRankingOut:
    """Os maiores do território no ano, todos os municípios dele incluídos (ADR-0034, 4)."""
    return svc.ranking(ctx, lens=lens, geography_key=geography_key, year=year, page=page)


@router.get("/table", response_model=ContasTableOut, summary="Tabela paginada")
def table(
    svc: Svc,
    ctx: CCtx,
    periods: Periods,
    geography_key: GeoQ = "brasil:1",
    lens: LensQ = "A",
    group_by: Annotated[str, Query(pattern=ID, description="territory, recipient ou dimensão.")] = (
        "territory"
    ),
    filters: Annotated[
        list[str] | None,
        Query(
            alias="filter",
            description="dimensão:código (repetível), ex.: function:10. Até 10.",
        ),
    ] = None,
    sort: Annotated[Literal["value", "name"], Query()] = "value",
    page: PageQ = 1,
    include_intermediaries: bool = False,
) -> ContasTableOut:
    """Desdobra em todos os níveis, 10 linhas por página (ADR-0034, decisão 3)."""
    return svc.table(
        ctx,
        lens=lens,
        geography_key=geography_key,
        periods=periods,
        group_by=group_by,
        filters=_split(filters, 11),
        sort=sort,
        page=page,
        include_intermediaries=include_intermediaries,
    )


@router.get(
    "/favorecidos/{recipient_id}",
    response_model=RecipientProfileOut,
    summary="Ficha do favorecido",
)
def recipient(
    svc: Svc,
    ctx: CCtx,
    response: Response,
    periods: Periods,
    recipient_id: Annotated[str, Path(pattern=r"^[0-9a-f]{16}$")],
) -> RecipientProfileOut:
    """O que o favorecido recebeu, por lente, ano, mês e órgão.

    Fichas de pessoa física não são indexadas por buscadores (ADR-0031, 5.6).
    """
    profile = svc.recipient(ctx, recipient_id, periods)
    if profile.recipient.is_natural_person:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return profile


@router.get("/busca", response_model=ContasSearchOut, summary="Busca")
def search(
    svc: Svc,
    ctx: CCtx,
    q: Annotated[str, Query(min_length=3, max_length=80)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> ContasSearchOut:
    """Favorecidos PJ, órgãos, programas e ações (pessoas físicas ficam fora)."""
    return svc.search(ctx, q, limit)


@router.get("/execucao", response_model=ContasExecutionOut, summary="Execução da despesa")
def execution(
    svc: Svc,
    ctx: CCtx,
    periods: Periods,
    dimension: Annotated[str, Query(pattern=ID)] = "function",
    filters: Annotated[list[str] | None, Query(alias="filter")] = None,
    page: PageQ = 1,
) -> ContasExecutionOut:
    """Empenhado, liquidado, pago e restos a pagar por categoria (lente C)."""
    return svc.execution(
        ctx, periods=periods, dimension=dimension, filters=_split(filters, 11), page=page
    )
