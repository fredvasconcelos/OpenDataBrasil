"""Catálogo: release, fontes, datasets e indicadores."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from odb_api.gold import NotFoundError
from odb_api.routes.common import ERRORS, ID, Ctx, Deps
from odb_api.schemas import (
    DatasetOut,
    IndicatorOut,
    LicenseOut,
    ReleaseOut,
    SourceOut,
    TableVersionOut,
    TreeNodeOut,
)

router = APIRouter(prefix="/api/v1", tags=["catálogo"], responses=ERRORS)


@router.get("/release", response_model=ReleaseOut, summary="Release ativo")
def release(ctx: Ctx) -> ReleaseOut:
    """Release vigente e as versões Delta de suas tabelas."""
    r = ctx.release
    return ReleaseOut(
        release_id=r.release_id,
        scope=r.scope,
        activated_at=r.activated_at.isoformat() if r.activated_at else None,
        code_version=r.code_version,
        tables=[
            TableVersionOut(table_id=t.table_id, delta_version=t.delta_version)
            for t in r.tables.values()
        ],
    )


@router.get("/sources", response_model=list[SourceOut], summary="Fontes")
def sources(d: Deps) -> list[SourceOut]:
    """Fontes de dados cadastradas."""
    return [SourceOut(**s) for s in d.catalog.sources()]


def _dataset(row: dict[str, object]) -> DatasetOut:
    return DatasetOut(
        dataset_id=str(row["dataset_id"]),
        source_id=str(row["source_id"]),
        official_id=str(row["official_id"]),
        title=str(row["title"]),
        description=str(row["description"]),
        periodicity=str(row["periodicity"]),
        reference_url=None if row["reference_url"] is None else str(row["reference_url"]),
        access_classification=str(row["access_classification"]),
        license=LicenseOut(
            license_id=str(row["license_id"]),
            name=str(row["license_name"]),
            url=None if row["license_url"] is None else str(row["license_url"]),
            conditions=str(row["conditions"]),
            review_status=str(row["review_status"]),
        ),
    )


@router.get("/datasets", response_model=list[DatasetOut], summary="Datasets")
def datasets(d: Deps) -> list[DatasetOut]:
    """Datasets habilitados, com licença."""
    return [_dataset(r) for r in d.catalog.datasets()]


@router.get("/datasets/{dataset_id}", response_model=DatasetOut, summary="Dataset")
def dataset(d: Deps, dataset_id: Annotated[str, Path(pattern=r"^[a-z0-9\-]{1,80}$")]) -> DatasetOut:
    """Um dataset."""
    found = d.catalog.datasets(dataset_id)
    if not found:
        msg = f"dataset inexistente: {dataset_id}"
        raise NotFoundError(msg)
    return _dataset(found[0])


def _indicator(row: dict[str, object]) -> IndicatorOut:
    return IndicatorOut.model_validate(
        {k: row.get(k) for k in IndicatorOut.model_fields}
        | {
            k: list(row.get(k) or [])  # type: ignore[call-overload]
            for k in ("theme_path", "classification_ids", "available_levels", "periods", "caveats")
        }
    )


@router.get("/indicators", response_model=list[IndicatorOut], summary="Indicadores")
def indicators(
    d: Deps,
    ctx: Ctx,
    q: Annotated[
        str | None, Query(max_length=80, description="Texto no nome ou descrição.")
    ] = None,
) -> list[IndicatorOut]:
    """Indicadores publicados no release ativo, com busca simples por texto."""
    out = []
    needle = (q or "").casefold()
    for row in d.gold.indicators(ctx).values():
        text = f"{row['name']} {row['description']} {' '.join(row['theme_path'] or [])}"
        if needle in text.casefold():
            out.append(_indicator(row))
    return out


@router.get("/indicators/tree", response_model=list[TreeNodeOut], summary="Árvore temática")
def tree(d: Deps, ctx: Ctx) -> list[TreeNodeOut]:
    """Árvore temática da Gold: grupo → indicador → classificação → categoria."""
    return [TreeNodeOut(**r) for r in d.gold.tree(ctx)]


@router.get("/indicators/{indicator_id}", response_model=IndicatorOut, summary="Indicador")
def indicator(d: Deps, ctx: Ctx, indicator_id: Annotated[str, Path(pattern=ID)]) -> IndicatorOut:
    """Metadados de um indicador no release ativo."""
    row = d.gold.indicators(ctx).get(indicator_id)
    if row is None:
        msg = f"indicador não publicado: {indicator_id}"
        raise NotFoundError(msg)
    return _indicator(row)
