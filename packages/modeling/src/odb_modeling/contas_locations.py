"""Complemento da Gold da lente C com o localizador original da CGU (ADR-0045).

Não converte nomes em códigos IBGE nem atribui o gasto ao recebedor. O fato antigo
permanece no manifesto: este complemento tem grão mais fino e reconciliação exata.
"""

from __future__ import annotations

import hashlib

import polars as pl

from odb_modeling import contas
from odb_modeling.contas_contracts import FACT_FEDERAL_BUDGET_EXECUTION
from odb_processing.contracts import Contract

# Ordem fixa para a identidade técnica. Textos oficiais ficam preservados separadamente.
LOCATION_FIELDS = (
    "uf",
    "municipality_name_source",
    "locator_code",
    "locator_name",
    "locator_acronym",
    "locator_description",
    "subtitle_code",
    "subtitle_name",
)
LOCATION_NAMES = {field: f"location_{field}" for field in LOCATION_FIELDS}
FACT_EXECUTION_LOCATION = Contract(
    name="fact_federal_execution_location",
    version="1.0.0",
    schema={
        **FACT_FEDERAL_BUDGET_EXECUTION.schema,
        "location_key": pl.String(),
        **dict.fromkeys(LOCATION_NAMES.values(), pl.String()),
    },
    key=(*FACT_FEDERAL_BUDGET_EXECUTION.key, "location_key"),
    required=(*FACT_FEDERAL_BUDGET_EXECUTION.required, "location_key"),
    partition_by=("year",),
)


def _location_id(value: str) -> str:
    """SHA-256 integral do JSON dos campos originais, nunca um código geográfico oficial."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def execution_locations(silver: pl.LazyFrame, dims: contas.Dimensions) -> pl.DataFrame:
    """Agrupa as fases preservando cada combinação de campos de localização da fonte."""
    locations = (
        silver.select(LOCATION_FIELDS)
        .unique()
        .collect(engine="streaming")
        .with_columns(
            pl.struct(LOCATION_FIELDS)
            .struct.json_encode()
            .map_elements(_location_id, return_dtype=pl.String())
            .alias("location_key")
        )
    )
    if locations["location_key"].n_unique() != locations.height:
        msg = "colisão na identidade dos localizadores"
        raise ValueError(msg)
    frame = contas._join_keys(silver, dims, ("ug", "action", "nature", "author"))
    frame = frame.join(locations.lazy(), on=list(LOCATION_FIELDS), how="left", nulls_equal=True)
    keys = [name for name in FACT_FEDERAL_BUDGET_EXECUTION.key if name != "period"]
    return (
        frame.group_by("period", *keys, "location_key", *LOCATION_FIELDS)
        .agg(
            *(pl.col(name).sum().alias(name) for name in contas.EXECUTION_MEASURES),
            pl.len().cast(pl.Int32).alias("source_lines"),
        )
        .with_columns(
            contas.gold_period(),
            pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"),
        )
        .rename(LOCATION_NAMES)
        .select(
            [pl.col(name).cast(dtype) for name, dtype in FACT_EXECUTION_LOCATION.schema.items()]
        )
        .collect(engine="streaming")
    )


def reconcile_locations(located: pl.DataFrame, original: pl.DataFrame) -> bool:
    """Confere cada chave antiga e as seis fases em Decimal, incluindo sinais e linhas."""
    old = FACT_FEDERAL_BUDGET_EXECUTION
    columns = [*contas.EXECUTION_MEASURES, "source_lines"]
    collapsed = located.group_by(old.key).agg(*(pl.col(name).sum() for name in columns))
    expected = original.select(*old.key, *columns)
    return collapsed.sort(old.key).equals(expected.sort(old.key))
