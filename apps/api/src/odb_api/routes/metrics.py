"""Métricas de acesso do portal (ADR-0027): só leitura do banco ``odb_metrics``.

Contagens de visualizações, aberturas de indicador e downloads; nunca de pessoas (o
portal não usa cookies). Sem coleta, as três rotas respondem 404.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response

from odb_api.gold import NotFoundError
from odb_api.metrics import (
    MAX_DATASETS,
    GeoLevel,
    MetricsService,
    Period,
    PeriodKey,
    Sort,
    kpi_titles,
    resolve_period,
)
from odb_api.routes.common import ERRORS, Deps
from odb_api.schemas import MetricsDatasetsOut, MetricsGeoOut, MetricsSummaryOut

router = APIRouter(prefix="/api/v1/metrics", tags=["métricas"], responses=ERRORS)

# Mesmo ciclo do agregador e do cache do serviço.
_CACHE_CONTROL = "public, max-age=300"

PeriodQ = Annotated[
    PeriodKey, Query(description="7d, 30d e 12m terminam hoje; custom exige from e to.")
]
FromQ = Annotated[
    date | None, Query(alias="from", description="Início do período custom (AAAA-MM-DD).")
]
ToQ = Annotated[date | None, Query(description="Fim do período custom (AAAA-MM-DD), até hoje.")]


def _service(d: Deps) -> MetricsService:
    if d.metrics is None:
        msg = "a coleta de acessos ainda não começou"
        raise NotFoundError(msg)
    return d.metrics


def _period(
    service: MetricsService, period: PeriodKey, start: date | None, end: date | None
) -> Period:
    return resolve_period(period, start, end, service.today())


@router.get("/summary", response_model=MetricsSummaryOut, summary="Totais de acessos")
def summary(
    d: Deps, response: Response, period: PeriodQ = "30d", start: FromQ = None, to: ToQ = None
) -> MetricsSummaryOut:
    """Visualizações, aberturas de indicador, downloads e países no período."""
    service = _service(d)
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return service.summary(_period(service, period, start, to))


@router.get("/geo", response_model=MetricsGeoOut, summary="Acessos por lugar")
def geo(
    d: Deps,
    response: Response,
    level: Annotated[GeoLevel, Query(description="pais, regiao ou uf.")],
    within: Annotated[
        str | None,
        Query(
            pattern=r"^(pais:BR|regiao:[1-5])$",
            description="regiao exige pais:BR; uf aceita pais:BR ou regiao:N.",
        ),
    ] = None,
    period: PeriodQ = "30d",
    start: FromQ = None,
    to: ToQ = None,
) -> MetricsGeoOut:
    """Visualizações por País, Grande Região ou Estado, com supressão abaixo de 5."""
    service = _service(d)
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return service.geo(level, within, _period(service, period, start, to))


@router.get("/datasets", response_model=MetricsDatasetsOut, summary="Indicadores mais acessados")
def datasets(
    d: Deps,
    response: Response,
    sort: Annotated[Sort, Query(description="views (aberturas) ou downloads.")] = "views",
    limit: Annotated[int, Query(ge=1, le=MAX_DATASETS)] = 10,
    period: PeriodQ = "30d",
    start: FromQ = None,
    to: ToQ = None,
) -> MetricsDatasetsOut:
    """Indicadores mais abertos ou baixados; título e tema vêm do release ativo."""
    service = _service(d)
    response.headers["Cache-Control"] = _CACHE_CONTROL
    ctx = d.resolver.current()
    titles = service.titles(ctx.release_id, lambda: kpi_titles(d.kpis.serialized(ctx)[0]))
    return service.datasets(sort, limit, _period(service, period, start, to), titles)
