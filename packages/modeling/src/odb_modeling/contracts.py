"""Contratos das tabelas Gold (ADR-0008).

As dimensões e a estrutura universal têm schema fixo. Os fatos temáticos têm
schema derivado do catálogo semântico (classificações e medidas declaradas) e
levam a versão do catálogo.
"""

from __future__ import annotations

import polars as pl

from odb_processing.contracts import Contract
from odb_processing.values import VALUE_DTYPE
from odb_semantics import FactConfig, SemanticCatalog

S = pl.String()
I16 = pl.Int16()
I32 = pl.Int32()
I64 = pl.Int64()
B = pl.Boolean()
LS = pl.List(pl.String())

DIM_GEOGRAPHY = Contract(
    name="dim_geography",
    version="1.0.0",
    schema={
        "geography_key": S,
        "level_id": S,
        "level_rank": I16,
        "level_name": S,
        "territory_code": S,
        "name": S,
        "parent_key": S,
        "region_code": S,
        "uf_code": S,
        "uf_abbreviation": S,
        "intermediate_region_code": S,
        "immediate_region_code": S,
        "in_reference": B,
        "reference": S,
    },
    key=("geography_key",),
    required=("geography_key", "level_id", "level_rank", "territory_code", "name", "in_reference"),
    partition_by=(),
)

BRIDGE_GEOGRAPHY_ANCESTOR = Contract(
    name="bridge_geography_ancestor",
    version="1.0.0",
    schema={
        "geography_key": S,
        "ancestor_key": S,
        "ancestor_level": S,
        "ancestor_rank": I16,
        "distance": I16,
    },
    key=("geography_key", "ancestor_key"),
    required=("geography_key", "ancestor_key", "ancestor_level", "ancestor_rank", "distance"),
    partition_by=(),
)

DIM_PERIOD = Contract(
    name="dim_period",
    version="1.0.0",
    schema={
        "period": S,
        "period_type": S,
        "year": I32,
        "start_date": pl.Date(),
        "end_date": pl.Date(),
    },
    key=("period",),
    required=("period", "period_type", "year", "start_date", "end_date"),
    partition_by=(),
)

DIM_CLASSIFICATION = Contract(
    name="dim_classification",
    version="1.0.0",
    schema={
        "classification_id": S,
        "name": S,
        "source_dimension": S,
        "total_category_key": S,
        "partition_ids": LS,
    },
    key=("classification_id",),
    required=("classification_id", "name", "total_category_key"),
    partition_by=(),
)

DIM_CATEGORY = Contract(
    name="dim_category",
    version="1.0.0",
    schema={
        "category_key": S,
        "classification_id": S,
        "category_id": S,
        "name": S,
        "is_total": B,
        "parent_category_key": S,
        "partition_id": S,
        "partition_label": S,
        "partition_exhaustive": B,
        "depth": I16,
        "sort_order": I32,
    },
    key=("category_key",),
    required=("category_key", "classification_id", "category_id", "name", "is_total", "depth"),
    partition_by=(),
)

DIM_BREAKDOWN = Contract(
    name="dim_breakdown",
    version="1.0.0",
    schema={
        "breakdown_key": S,
        "label": S,
        "category_keys": LS,
        "classification_ids": LS,
        "non_total_classifications": LS,
        "non_total_count": I16,
    },
    key=("breakdown_key",),
    required=("breakdown_key", "label", "non_total_count"),
    partition_by=(),
)

INCOMPATIBILITY = pl.Struct({"indicator": S, "reason": S})

DIM_INDICATOR = Contract(
    name="dim_indicator",
    version="1.0.0",
    schema={
        "indicator_id": S,
        "name": S,
        "description": S,
        "scope": S,
        "dataset_id": S,
        "source_table_id": S,
        "source_variable_id": S,
        "source_variable_name": S,
        "unit": S,
        "additivity": S,
        "concept": S,
        "fact_table": S,
        "fact_column": S,
        "theme_path": LS,
        "node_key": S,
        "classification_ids": LS,
        "available_levels": LS,
        "periods": LS,
        "observation_count": I64,
        "caveats": LS,
        "incompatible_with": pl.List(INCOMPATIBILITY),
        "reference_url": S,
        "license_id": S,
    },
    key=("indicator_id",),
    required=("indicator_id", "name", "dataset_id", "unit", "additivity", "fact_table"),
    partition_by=(),
)

DIM_INDICATOR_NODE = Contract(
    name="dim_indicator_node",
    version="1.0.0",
    schema={
        "node_key": S,
        "parent_key": S,
        "node_type": S,
        "label": S,
        "depth": I16,
        "path_labels": LS,
        "indicator_id": S,
        "classification_id": S,
        "category_key": S,
        "sort_order": I32,
    },
    key=("node_key",),
    required=("node_key", "node_type", "label", "depth", "path_labels", "sort_order"),
    partition_by=(),
)

INDICATOR_OBSERVATION = Contract(
    name="indicator_observation",
    version="1.0.0",
    schema={
        "indicator_id": S,
        "dataset_id": S,
        "geography_key": S,
        "level_id": S,
        "period": S,
        "breakdown_key": S,
        "value": VALUE_DTYPE,
        "value_status": S,
        "value_raw": S,
        "value_decimals": pl.Int8(),
        "unit": S,
        "flags": LS,
        "source_table_id": S,
        "source_variable_id": S,
        "silver_table_version": I64,
        "bronze_artifact_id": S,
        "bronze_checksum_sha256": S,
        "gold_build_id": S,
    },
    key=("indicator_id", "geography_key", "period", "breakdown_key"),
    required=(
        "indicator_id",
        "dataset_id",
        "geography_key",
        "level_id",
        "period",
        "breakdown_key",
        "value_status",
        "value_raw",
        "unit",
        "source_table_id",
        "source_variable_id",
        "silver_table_version",
        "bronze_artifact_id",
        "bronze_checksum_sha256",
        "gold_build_id",
    ),
    partition_by=("dataset_id",),
)

F64 = pl.Float64()

# Geometria simplificada para mapas (§13.4). A geometria original fica na
# Silver (``territorial_mesh``) e o arquivo original na Bronze.
DIM_GEOMETRY = Contract(
    name="dim_geometry",
    version="1.0.0",
    schema={
        "geography_key": S,
        "level_id": S,
        "geometry_geojson": S,
        "vertex_count": I64,
        "bbox_min_lon": F64,
        "bbox_min_lat": F64,
        "bbox_max_lon": F64,
        "bbox_max_lat": F64,
        "tolerance_deg": F64,
        "coordinate_decimals": I16,
        # "official" (malha publicada) ou "union:<nível>" (união das geometrias do nível).
        "derivation": S,
        "crs": S,
        "source_dataset_id": S,
        "reference_year": S,
        "silver_table_version": I64,
        "bronze_artifact_id": S,
    },
    key=("geography_key",),
    required=(
        "geography_key",
        "level_id",
        "geometry_geojson",
        "vertex_count",
        "tolerance_deg",
        "derivation",
        "crs",
        "source_dataset_id",
        "reference_year",
        "silver_table_version",
    ),
    partition_by=(),
)

FIXED_CONTRACTS: tuple[Contract, ...] = (
    DIM_GEOGRAPHY,
    BRIDGE_GEOGRAPHY_ANCESTOR,
    DIM_PERIOD,
    DIM_CLASSIFICATION,
    DIM_CATEGORY,
    DIM_BREAKDOWN,
    DIM_INDICATOR,
    DIM_INDICATOR_NODE,
    INDICATOR_OBSERVATION,
)


def fact_contract(catalog: SemanticCatalog, fact: FactConfig, *, flags: bool) -> Contract:
    """Contrato de um fato temático, derivado do catálogo semântico.

    Granularidade: território x período x categorias das classificações do fato.
    Cada indicador do fato vira uma medida (``<coluna>``) com o estado do valor
    (``<coluna>_status``).
    """
    schema: dict[str, pl.DataType] = {"geography_key": S, "level_id": S, "period": S}
    schema.update(dict.fromkeys(fact.classifications.values(), S))
    for indicator in catalog.indicators_of(fact.id):
        schema[indicator.column] = VALUE_DTYPE
        schema[f"{indicator.column}_status"] = S
    if flags:
        schema["pending_installation"] = B
    schema["silver_table_version"] = I64
    schema["gold_build_id"] = S
    key = ("geography_key", "period", *fact.classifications.values())
    return Contract(
        name=fact.id,
        version=catalog.config_version,
        schema=schema,
        key=key,
        required=(*key, "level_id", "silver_table_version", "gold_build_id"),
        partition_by=(),
    )
