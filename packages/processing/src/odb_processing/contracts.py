"""Contratos de schema versionados da Silver (§9.3).

A versão sobe a cada mudança. Acrescentar uma coluna é compatível (``minor``).
Remover coluna ou trocar tipo é incompatível e bloqueia a escrita, salvo nova
versão ``major`` aprovada.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import polars as pl

from odb_processing import contas_layout as _contas
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

TERRITORIAL_MESH = Contract(
    name="territorial_mesh",
    version="1.0.0",
    schema={
        "dataset_id": pl.String(),
        "reference_year": pl.String(),
        "level_id": pl.String(),
        "code": pl.String(),
        "name": pl.String(),
        "uf_abbreviation": pl.String(),
        "area_km2": pl.Float64(),
        "crs": pl.String(),
        # Geometria original, sem simplificação, em WKB.
        "geometry_wkb": pl.Binary(),
        "vertex_count": pl.Int64(),
        "source_member": pl.String(),
        **LINEAGE,
    },
    key=("dataset_id", "code"),
    required=(
        "dataset_id",
        "reference_year",
        "level_id",
        "code",
        "name",
        "crs",
        "geometry_wkb",
        "vertex_count",
        *LINEAGE,
    ),
    partition_by=("dataset_id",),
)

# ------------------------------------------------------------------ contas públicas
# ADR-0030 a 0035. Colunas da fonte em texto, com nomes em inglês como os demais contratos;
# os valores ficam também no original (``*_raw``, §9.4). A ordem das colunas segue as
# tuplas de ``odb_processing.contas``, as mesmas que conferem o cabeçalho da fonte.

_S = pl.String()


def _texts(columns: tuple[tuple[str, str], ...]) -> dict[str, pl.DataType]:
    return {name: _S for _, name in columns}


_DERIVED: dict[str, pl.DataType] = {
    "municipality_id": _S,
    "territory_status": _S,
    "territory_method": _S,
    "legal_nature_code": _S,
    "recipient_class": _S,
    "recipient_class_version": _S,
    # Versões Silver das referências usadas (TABMUN, DTB, cadastro PJ): mudar uma
    # referência refaz os meses, mesmo sem Bronze nova.
    "derivation_refs": _S,
}

CGU_TRANSFER = Contract(
    name="cgu_transfer",
    version="1.0.0",
    schema={
        "period": _S,
        "line_number": pl.Int64(),
        **_texts(_contas.TRANSFER_COLUMNS),
        "value": VALUE_DTYPE,
        **_DERIVED,
        **LINEAGE,
    },
    key=("period", "line_number"),
    required=(
        "period",
        "line_number",
        "period_raw",
        "transfer_type",
        "recipient_code",
        "value_raw",
        "value",
        "territory_status",
        "recipient_class",
        *LINEAGE,
    ),
    partition_by=("period",),
)

CGU_RECIPIENT_PAYMENT = Contract(
    name="cgu_recipient_payment",
    version="1.0.0",
    schema={
        "period": _S,
        "line_number": pl.Int64(),
        **_texts(_contas.PAYMENT_COLUMNS),
        "value": VALUE_DTYPE,
        **_DERIVED,
        **LINEAGE,
    },
    key=("period", "line_number"),
    required=(
        "period",
        "line_number",
        "period_raw",
        "recipient_code",
        "management_unit_code",
        "value_raw",
        "value",
        "territory_status",
        "recipient_class",
        *LINEAGE,
    ),
    partition_by=("period",),
)

_EXECUTION_VALUES = tuple(name for _, name in _contas.EXECUTION_VALUES)

CGU_BUDGET_EXECUTION = Contract(
    name="cgu_budget_execution",
    version="1.0.0",
    schema={
        "period": _S,
        "line_number": pl.Int64(),
        **_texts(_contas.EXECUTION_COLUMNS),
        **dict.fromkeys(_EXECUTION_VALUES, VALUE_DTYPE),
        **LINEAGE,
    },
    key=("period", "line_number"),
    required=(
        "period",
        "line_number",
        "period_raw",
        "management_unit_code",
        "action_code",
        *(f"{v}_raw" for v in _EXECUTION_VALUES),
        *_EXECUTION_VALUES,
        *LINEAGE,
    ),
    partition_by=("period",),
)

SIAFI_MUNICIPALITY = Contract(
    name="siafi_municipality",
    version="1.0.0",
    schema={
        "dataset_id": _S,
        "line_number": pl.Int64(),
        **dict.fromkeys(_contas.TABMUN_COLUMNS, _S),
        "current_name": _S,
        "former_name": _S,
        **LINEAGE,
    },
    key=("dataset_id", "siafi_code"),
    required=("dataset_id", "siafi_code", "uf", "municipality_id", "current_name", *LINEAGE),
    partition_by=("dataset_id",),
)

CGU_LEGAL_ENTITY = Contract(
    name="cgu_legal_entity",
    version="1.0.0",
    schema={
        "snapshot": _S,
        "line_number": pl.Int64(),
        **_texts(_contas.LEGAL_ENTITY_COLUMNS),
        "cnae_description": _S,
        "cnae_section_code": _S,
        "cnae_section_description": _S,
        "legal_nature_description": _S,
        "legal_nature_type_code": _S,
        "legal_nature_type_description": _S,
        **LINEAGE,
    },
    key=("snapshot", "recipient_code"),
    required=("snapshot", "recipient_code", *LINEAGE),
    partition_by=("snapshot",),
)

_SIOP_KEY = (
    "fiscal_year",
    "sphere",
    "budget_unit_code",
    "function_code",
    "subfunction_code",
    "program_code",
    "action_code",
)

SIOP_BUDGET_ACTION = Contract(
    name="siop_budget_action",
    version="1.0.0",
    schema={"line_number": pl.Int64(), **_texts(_contas.SIOP_ACTION_COLUMNS), **LINEAGE},
    key=_SIOP_KEY,
    required=(*_SIOP_KEY, "title", *LINEAGE),
    partition_by=("fiscal_year",),
)

SIOP_BUDGET_PLAN = Contract(
    name="siop_budget_plan",
    version="1.0.0",
    schema={"line_number": pl.Int64(), **_texts(_contas.SIOP_PLAN_COLUMNS), **LINEAGE},
    key=(*_SIOP_KEY, "budget_plan_code"),
    required=(*_SIOP_KEY, "budget_plan_code", "title", *LINEAGE),
    partition_by=("fiscal_year",),
)

CONTRACTS = {
    c.name: c
    for c in (
        SIDRA_OBSERVATION,
        DTB_MUNICIPALITY,
        TERRITORIAL_MESH,
        CGU_TRANSFER,
        CGU_RECIPIENT_PAYMENT,
        CGU_BUDGET_EXECUTION,
        SIAFI_MUNICIPALITY,
        CGU_LEGAL_ENTITY,
        SIOP_BUDGET_ACTION,
        SIOP_BUDGET_PLAN,
    )
}


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
