"""Territórios e geometrias."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response

from odb_api.routes.common import ERRORS, GEOGRAPHY_KEY, ID, Ctx, Deps
from odb_api.schemas import GeographyOut

router = APIRouter(prefix="/api/v1", tags=["territórios"], responses=ERRORS)


def accepts_gzip(value: str) -> bool:
    """Respeita a preferência explícita de gzip, inclusive q=0 sobre o curinga."""
    preferences: dict[str, float] = {}
    for item in value.lower().split(","):
        encoding, *parameters = item.strip().split(";")
        quality = 1.0
        for parameter in parameters:
            name, _, raw = parameter.strip().partition("=")
            if name == "q":
                try:
                    quality = float(raw)
                except ValueError:
                    quality = 0.0
        preferences[encoding.strip()] = quality if 0 <= quality <= 1 else 0.0
    return preferences.get("gzip", preferences.get("*", 0.0)) > 0


def _geo(row: dict[str, object]) -> GeographyOut:
    return GeographyOut.model_validate({k: row.get(k) for k in GeographyOut.model_fields})


@router.get("/geographies", response_model=list[GeographyOut], summary="Busca de territórios")
def geographies(
    d: Deps,
    ctx: Ctx,
    q: Annotated[str | None, Query(max_length=80)] = None,
    level: Annotated[list[str] | None, Query(description="Níveis (repetível).")] = None,
    within: Annotated[str | None, Query(pattern=GEOGRAPHY_KEY)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[GeographyOut]:
    """Busca por nome (ignora acentos e caixa), nível e recorte."""
    levels = [lvl for lvl in level or [] if lvl]
    return [
        _geo(r)
        for r in d.gold.search_geographies(ctx, text=q, levels=levels, within=within, limit=limit)
    ]


@router.get("/geographies/{geography_key}", response_model=GeographyOut, summary="Território")
def geography(
    d: Deps, ctx: Ctx, geography_key: Annotated[str, Path(pattern=GEOGRAPHY_KEY)]
) -> GeographyOut:
    """Um território."""
    return _geo(d.gold.geography(ctx, geography_key))


@router.get(
    "/geometries/{level}",
    summary="Geometria de um nível (GeoJSON)",
    response_class=Response,
    responses={200: {"content": {"application/geo+json": {}}}},
)
def geometries(
    request: Request,
    d: Deps,
    ctx: Ctx,
    level: Annotated[str, Path(pattern=ID)],
    within: Annotated[str | None, Query(pattern=GEOGRAPHY_KEY)] = None,
) -> Response:
    """``FeatureCollection`` simplificada para mapas (``dim_geometry`` do release)."""
    compressed = accepts_gzip(request.headers.get("accept-encoding", ""))
    variant = ":gzip" if compressed else ""
    etag = f'"{ctx.release_id}:{level}:{within or ""}{variant}"'
    headers = {
        "ETag": etag,
        "Cache-Control": "public, max-age=300",
        "X-ODB-Release": ctx.release_id,
        "Vary": "Accept-Encoding",
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    body = d.gold.geometry_payload(ctx, level, within, compressed=compressed)
    if compressed:
        headers["Content-Encoding"] = "gzip"
    return Response(body, media_type="application/geo+json", headers=headers)
