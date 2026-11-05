"""Geometria simplificada para mapas (``dim_geometry``, §13.4).

Entrada: a Silver ``territorial_mesh`` (malhas oficiais, geometria original em
WKB), a ``dim_geography`` e a ``bridge_geography_ancestor`` da mesma construção.

* Nível com malha oficial: um polígono por território da ``dim_geography``.
  Polígonos sem território correspondente (as lagoas da malha municipal) ficam
  de fora e são informados.
* Nível derivado (``derive_from``): união (``union_all``) das geometrias
  originais do nível de origem, agrupadas pelo ancestral. Grandes Regiões e Brasil saem das UFs, sem
  tabela de correspondência própria.

A simplificação usa ``shapely.coverage_simplify``, que preserva as divisas
compartilhadas entre vizinhos (sem frestas nem sobreposições). As coordenadas
são arredondadas depois, só para reduzir o tamanho do GeoJSON. O arredondamento
pode cruzar arestas de feições estreitas. Essas geometrias são reparadas com
``make_valid`` estrutural (só polígonos) e contadas no relatório. Na malha
municipal de 2022, com 4 casas, a maior perda de área medida foi de 0,2%.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
import shapely

from odb_modeling.contracts import DIM_GEOMETRY
from odb_semantics import GeometryLevel, geography_key


class GeometryError(ValueError):
    """Geometria impossível de construir com a configuração e as entradas."""


@dataclass
class GeometryReport:
    """O que ficou de fora e o que falta, por nível."""

    dropped: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    missing: dict[str, list[str]] = field(default_factory=dict)
    invalid: list[str] = field(default_factory=list)
    repaired: list[str] = field(default_factory=list)


Originals = dict[str, dict[str, tuple[Any, dict[str, Any]]]]


def _round(
    keys: Sequence[str], geoms: Sequence[Any], decimals: int, report: GeometryReport
) -> list[Any]:
    def snap(coords: Any) -> Any:
        return np.round(coords, decimals)

    out = []
    for key, geom in zip(keys, geoms, strict=True):
        rounded = shapely.transform(geom, snap)
        if not rounded.is_valid:
            rounded = shapely.make_valid(rounded, method="structure", keep_collapsed=False)
            report.repaired.append(key)
        out.append(rounded)
    return out


def _originals(
    mesh: pl.DataFrame, levels: Sequence[GeometryLevel], known: set[str], report: GeometryReport
) -> Originals:
    """Geometria original de cada nível oficial: chave → (geometria, linha da malha)."""
    out: Originals = {}
    for cfg in levels:
        if cfg.dataset is None:
            continue
        rows = mesh.filter(pl.col("dataset_id") == cfg.dataset)
        if rows.is_empty():
            msg = f"malha {cfg.dataset} sem linhas na Silver"
            raise GeometryError(msg)
        if rows.filter(pl.col("level_id") != cfg.level).height:
            msg = f"malha {cfg.dataset} não é do nível {cfg.level}"
            raise GeometryError(msg)
        geoms = shapely.from_wkb(rows["geometry_wkb"].to_list())
        level: dict[str, tuple[Any, dict[str, Any]]] = {}
        dropped: list[dict[str, str]] = []
        for geom, row in zip(geoms, rows.drop("geometry_wkb").iter_rows(named=True), strict=True):
            key = geography_key(cfg.level, row["code"])
            if key in known:
                level[key] = (geom, row)
            else:
                dropped.append({"code": row["code"], "name": row["name"]})
        out[cfg.level] = level
        if dropped:
            report.dropped[cfg.level] = dropped
    return out


def _level_geometries(
    cfg: GeometryLevel, originals: Originals, bridge: pl.DataFrame
) -> tuple[list[str], list[Any], list[dict[str, Any]], str]:
    """Chaves, geometrias (não simplificadas), linhas de origem e derivação do nível."""
    if cfg.dataset is not None:
        items = originals[cfg.level]
        keys = sorted(items)
        return keys, [items[k][0] for k in keys], [items[k][1] for k in keys], "official"
    base = originals[str(cfg.derive_from)]
    parents = bridge.filter(
        (pl.col("ancestor_level") == cfg.level) & pl.col("geography_key").is_in(list(base))
    ).select("geography_key", "ancestor_key")
    groups: dict[str, list[str]] = {}
    for child, parent in parents.iter_rows():
        groups.setdefault(parent, []).append(child)
    keys = sorted(groups)
    # union_all, e não coverage_union_all: as divisas das malhas oficiais não têm
    # vértices exatamente coincidentes (a união por cobertura falha nas UFs reais).
    geoms = [shapely.union_all([base[c][0] for c in groups[k]]) for k in keys]
    # Linhagem do primeiro filho: todos vêm da mesma malha e do mesmo artefato.
    sources = [base[groups[k][0]][1] for k in keys]
    return keys, geoms, sources, f"union:{cfg.derive_from}"


def build_dim_geometry(
    mesh: pl.DataFrame,
    geography: pl.DataFrame,
    bridge: pl.DataFrame,
    levels: Sequence[GeometryLevel],
    *,
    silver_version: int,
) -> tuple[pl.DataFrame, GeometryReport]:
    """Uma linha por território com geometria, em GeoJSON simplificado."""
    report = GeometryReport()
    originals = _originals(mesh, levels, set(geography["geography_key"].to_list()), report)
    out: list[dict[str, Any]] = []
    for cfg in levels:
        keys, geoms, sources, derivation = _level_geometries(cfg, originals, bridge)
        expected = geography.filter(pl.col("level_id") == cfg.level)["geography_key"].to_list()
        missing = sorted(set(expected) - set(keys))
        if missing:
            report.missing[cfg.level] = missing
        simplified = _round(
            keys, shapely.coverage_simplify(geoms, cfg.tolerance), cfg.decimals, report
        )
        for key, geom, src in zip(keys, simplified, sources, strict=True):
            if (
                geom.is_empty
                or not geom.is_valid
                or geom.geom_type not in {"Polygon", "MultiPolygon"}
            ):
                report.invalid.append(key)
            minx, miny, maxx, maxy = shapely.bounds(geom).tolist()
            out.append(
                {
                    "geography_key": key,
                    "level_id": cfg.level,
                    "geometry_geojson": shapely.to_geojson(geom),
                    "vertex_count": int(shapely.get_num_coordinates(geom)),
                    "bbox_min_lon": minx,
                    "bbox_min_lat": miny,
                    "bbox_max_lon": maxx,
                    "bbox_max_lat": maxy,
                    "tolerance_deg": cfg.tolerance,
                    "coordinate_decimals": cfg.decimals,
                    "derivation": derivation,
                    "crs": src["crs"],
                    "source_dataset_id": src["dataset_id"],
                    "reference_year": src["reference_year"],
                    "silver_table_version": silver_version,
                    "bronze_artifact_id": src["bronze_artifact_id"],
                }
            )
    return pl.DataFrame(out, schema=DIM_GEOMETRY.frame_schema()), report
