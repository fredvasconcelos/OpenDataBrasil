"""Contratos de schema versionados da Silver (§9.3).

A versão sobe a cada mudança. Acrescentar uma coluna é compatível (``minor``).
Remover coluna ou trocar tipo é incompatível e bloqueia a escrita, salvo nova
versão ``major`` aprovada.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import polars as pl

from odb_processing.values import VALUE_DTYPE

UTC_TS = pl.Datetime("us", "UTC")

LINEAGE: dict[str, pl.DataType] = {
    "bronze_artifact_id": pl.String(),
    "bronze_checksum_sha256": pl.String(),
    "source_url": pl.String(),
    "retrieved_at": UTC_TS,
    "ingestion_id": pl.String(),
    "silver_run_id": pl.String(),
    "processed_at": UTC_TS,
}

CLASSIFICATION = pl.Struct(
    {"dimension": pl.String(), "category_id": pl.String(), "category_name": pl.String()}
)


@dataclass(frozen=True, slots=True)
class Contract:
    """Schema esperado de uma tabela Silver."""

    name: str
    version: str
    schema: dict[str, pl.DataType]
    key: tuple[str, ...]
    required: tuple[str, ...]
    partition_by: tuple[str, ...]

    def frame_schema(self) -> pl.Schema:
        """Schema Polars na ordem do contrato."""
        return pl.Schema(self.schema)


SIDRA_OBSERVATION = Contract(
    name="sidra_observation",
    version="1.0.0",
    schema={
        "table_id": pl.String(),
        "variable_id": pl.String(),
        "variable_name": pl.String(),
        "unit_id": pl.String(),
        "unit_name": pl.String(),
        "territorial_level": pl.String(),
        "territorial_level_name": pl.String(),
        "territory_id": pl.String(),
        "territory_name": pl.String(),
        "period": pl.String(),
        "period_name": pl.String(),
        "classification_key": pl.String(),
        "classifications": pl.List(CLASSIFICATION),
        "value_raw": pl.String(),
        "value": VALUE_DTYPE,
        "value_status": pl.String(),
        "value_decimals": pl.Int8(),
        **LINEAGE,
    },
    key=(
        "table_id",
        "variable_id",
        "territorial_level",
        "territory_id",
        "period",
        "classification_key",
    ),
    required=(
        "table_id",
        "variable_id",
        "territorial_level",
        "territory_id",
        "period",
        "classification_key",
        "value_raw",
        "value_status",
        *LINEAGE,
    ),
    partition_by=("table_id",),
)

DTB_MUNICIPALITY = Contract(
    name="dtb_municipality",
    version="1.0.0",
    schema={
        "reference_year": pl.String(),
        "reference_date": pl.Date(),
        "region_id": pl.String(),
        "region_name": pl.String(),
        "uf_id": pl.String(),
        "uf_name": pl.String(),
        "intermediate_region_id": pl.String(),
        "intermediate_region_name": pl.String(),
        "immediate_region_id": pl.String(),
        "immediate_region_name": pl.String(),
        "municipality_local_code": pl.String(),
        "municipality_id": pl.String(),
        "municipality_name": pl.String(),
        "source_member": pl.String(),
        **LINEAGE,
    },
    key=("reference_year", "municipality_id"),
    required=(
        "reference_year",
        "reference_date",
        "region_id",
        "uf_id",
        "municipality_id",
        "municipality_name",
        *LINEAGE,
    ),
    partition_by=("reference_year",),
)

CONTRACTS = {c.name: c for c in (SIDRA_OBSERVATION, DTB_MUNICIPALITY)}


class SchemaChange(StrEnum):
    """Classificação de uma diferença de schema."""

    IDENTICAL = "identical"
    COMPATIBLE_ADDITION = "compatible_addition"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True, slots=True)
class SchemaComparison:
    """Resultado da comparação entre a tabela existente e o contrato."""

    change: SchemaChange
    details: tuple[str, ...] = ()


def compare_schema(existing: pl.Schema, contract: Contract) -> SchemaComparison:
    """Compara o schema de uma tabela existente com o contrato."""
    expected = contract.frame_schema()
    details: list[str] = []
    removed = [c for c in existing if c not in expected]
    changed = [
        f"{c}: {existing[c]} → {expected[c]}"
        for c in existing
        if c in expected and existing[c] != expected[c]
    ]
    added = [c for c in expected if c not in existing]
    if removed:
        details.append(f"colunas ausentes no contrato: {removed}")
    if changed:
        details.append(f"tipos alterados: {changed}")
    if removed or changed:
        return SchemaComparison(SchemaChange.INCOMPATIBLE, tuple(details))
    if added:
        return SchemaComparison(SchemaChange.COMPATIBLE_ADDITION, (f"colunas novas: {added}",))
    return SchemaComparison(SchemaChange.IDENTICAL)
