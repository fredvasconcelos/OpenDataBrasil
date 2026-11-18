"""Perfil Delta conservador da plataforma (ADR-0001, decisão 4).

Tabelas Silver/Gold devem permanecer em ``minReaderVersion=1`` e
``minWriterVersion=2``, sem table features. Este módulo verifica o perfil:

* **antes da escrita**, sobre o schema Polars, com uma lista explícita de tipos
  permitidos. Tipos fora da lista elevam o protocolo (datetime sem fuso gera
  ``timestampNtz``), quebram o writer (``Categorical``) ou perdem informação em
  silêncio (``UInt64`` vira ``long``);
* **depois da escrita**, sobre o protocolo e a configuração da tabela.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import polars as pl
from deltalake import DeltaTable

MAX_READER_VERSION = 1
MAX_WRITER_VERSION = 2
MAX_DECIMAL_PRECISION = 38

_SIMPLE_TYPES: tuple[type[pl.DataType], ...] = (
    pl.Boolean,
    pl.Int8,
    pl.Int16,
    pl.Int32,
    pl.Int64,
    pl.Float32,
    pl.Float64,
    pl.String,
    pl.Binary,
    pl.Date,
)

# Propriedades de tabela que ativam recursos fora do perfil.
_FORBIDDEN_CONFIG_PREFIXES = (
    "delta.enableDeletionVectors",
    "delta.columnMapping",
    "delta.enableTypeWidening",
    "delta.checkpointPolicy",
    "delta.enableRowTracking",
    "delta.enableChangeDataFeed",
)


class ProtocolViolationError(ValueError):
    """Schema ou tabela fora do perfil Delta conservador."""


@dataclass(frozen=True, slots=True)
class ProtocolReport:
    """Estado do protocolo de uma tabela Delta existente."""

    min_reader_version: int
    min_writer_version: int
    reader_features: tuple[str, ...]
    writer_features: tuple[str, ...]
    configuration: Mapping[str, str | None]


def _type_problem(dtype: object) -> str | None:  # noqa: PLR0911 - despacho por tipo
    if isinstance(dtype, type) and issubclass(dtype, pl.DataType):
        dtype = dtype()  # aceita tanto pl.Int64 quanto pl.Int64()
    if isinstance(dtype, _SIMPLE_TYPES):
        return None
    if isinstance(dtype, pl.Datetime):
        if dtype.time_zone != "UTC":
            return (
                f"{dtype}: datetimes devem ter time_zone='UTC' (sem fuso gera timestampNtz; "
                "converta com dt.convert_time_zone('UTC'))"
            )
        return None
    if isinstance(dtype, pl.Decimal):
        if dtype.precision is None or dtype.precision > MAX_DECIMAL_PRECISION:
            return f"{dtype}: decimal exige precisão explícita <= {MAX_DECIMAL_PRECISION}"
        return None
    if isinstance(dtype, pl.List):
        inner = _type_problem(dtype.inner)
        return f"List[{inner}]" if inner else None
    if isinstance(dtype, pl.Struct):
        for field in dtype.fields:
            inner = _type_problem(field.dtype)
            if inner:
                return f"Struct.{field.name}: {inner}"
        return None
    return f"{dtype}: tipo não permitido no perfil Delta (converta explicitamente)"


def validate_schema(schema: pl.Schema | Mapping[str, Any]) -> None:
    """Rejeita schemas cujos tipos não pertencem ao perfil conservador."""
    problems = [
        f"{name}: {problem}"
        for name, dtype in schema.items()
        if (problem := _type_problem(dtype)) is not None
    ]
    if problems:
        raise ProtocolViolationError("schema fora do perfil Delta: " + "; ".join(problems))


def inspect_table(table: DeltaTable) -> ProtocolReport:
    """Lê protocolo e configuração da versão carregada da tabela."""
    protocol = table.protocol()
    return ProtocolReport(
        min_reader_version=protocol.min_reader_version,
        min_writer_version=protocol.min_writer_version,
        reader_features=tuple(protocol.reader_features or ()),
        writer_features=tuple(protocol.writer_features or ()),
        configuration=dict(table.metadata().configuration),
    )


def validate_table(table: DeltaTable) -> ProtocolReport:
    """Garante que a tabela permanece no perfil conservador."""
    report = inspect_table(table)
    problems: list[str] = []
    if report.min_reader_version > MAX_READER_VERSION:
        problems.append(f"minReaderVersion={report.min_reader_version}")
    if report.min_writer_version > MAX_WRITER_VERSION:
        problems.append(f"minWriterVersion={report.min_writer_version}")
    if report.reader_features:
        problems.append(f"readerFeatures={list(report.reader_features)}")
    if report.writer_features:
        problems.append(f"writerFeatures={list(report.writer_features)}")
    problems.extend(
        f"configuração proibida {key}"
        for key in report.configuration
        if key.startswith(_FORBIDDEN_CONFIG_PREFIXES)
    )
    if problems:
        raise ProtocolViolationError("tabela fora do perfil Delta: " + ", ".join(problems))
    return report
