"""Dependências comuns das rotas."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, Query, Request, Response
from fastapi.exceptions import RequestValidationError

from odb_api.deps import ApiDeps
from odb_api.release import ReleaseContext
from odb_api.schemas import ErrorOut

GEOGRAPHY_KEY = r"^[a-z_]{2,32}:[0-9A-Za-z]{1,16}$"
ID = r"^[a-z][a-z0-9_]{0,63}$"
PERIOD = r"^[0-9A-Za-z]{1,16}$"


def deps(request: Request) -> ApiDeps:
    """Componentes da aplicação."""
    value: ApiDeps = request.app.state.deps
    return value


def context(response: Response, d: Annotated[ApiDeps, Depends(deps)]) -> ReleaseContext:
    """Release da requisição, informado no cabeçalho ``X-ODB-Release``."""
    ctx = d.resolver.current()
    response.headers["X-ODB-Release"] = ctx.release_id
    return ctx


def dimension_list(
    dimensions: Annotated[
        list[str] | None,
        Query(description="Dimensões do KPI (repetível ou separadas por vírgula), ex.: c86,c2."),
    ] = None,
) -> list[str]:
    """Lista de dimensões, aceitando ``a,b`` ou parâmetros repetidos."""
    out: list[str] = []
    for item in dimensions or []:
        out.extend(p.strip() for p in item.split(",") if p.strip())
    return out


def category_list(
    categories: Annotated[
        list[str] | None,
        Query(
            description=(
                "Filtro de categorias das dimensões detalhadas (repetível ou separadas por "
                "vírgula), ex.: c79:2670,c79:2681. Sem filtro numa dimensão: todas. Em "
                "indicadores somáveis, o Total vira a soma das categorias escolhidas."
            )
        ),
    ] = None,
) -> list[str]:
    """Lista de chaves de categoria, aceitando ``a,b`` ou parâmetros repetidos."""
    out: list[str] = []
    for item in categories or []:
        out.extend(p.strip() for p in item.split(",") if p.strip())
    return out


def period_list(
    periods: Annotated[
        list[str] | None,
        Query(
            description=(
                "Vários períodos (repetível ou separados por vírgula), ex.: 2025T1,2025T2. "
                "Na tabela, um grupo de colunas por período; com accumulate, o acumulado "
                "(ADR-0026)."
            )
        ),
    ] = None,
) -> list[str]:
    """Lista de códigos de período, aceitando ``a,b`` ou parâmetros repetidos."""
    out: list[str] = []
    for item in periods or []:
        out.extend(p.strip() for p in item.split(",") if p.strip())
    if any(not re.fullmatch(PERIOD, p) for p in out):
        raise RequestValidationError([{"loc": ("query", "periods"), "msg": "período inválido"}])
    return out


Deps = Annotated[ApiDeps, Depends(deps)]
Ctx = Annotated[ReleaseContext, Depends(context)]
Dims = Annotated[list[str], Depends(dimension_list)]
Cats = Annotated[list[str], Depends(category_list)]
Periods = Annotated[list[str], Depends(period_list)]


# Respostas de erro documentadas no OpenAPI (formato ``ErrorOut``).
ERRORS: dict[int | str, dict[str, object]] = {
    status: {"model": ErrorOut, "description": text}
    for status, text in (
        (404, "Recurso inexistente no release"),
        (422, "Regra semântica ou parâmetro inválido"),
        (429, "Limite de requisições"),
        (503, "Sem release ativo ou motor ocupado"),
        (504, "Tempo de consulta excedido"),
    )
}
