"""Motor SQL de leitura da plataforma."""

from odb_query_engine.contract import (
    PinnedTable,
    QueryEngineBusyError,
    QueryError,
    QueryRejectedError,
    QueryResult,
    QueryTimeoutError,
    ReadEngine,
    ReadQuery,
)
from odb_query_engine.duckdb_engine import DuckDBConfig, DuckDBReadEngine

__all__ = [
    "DuckDBConfig",
    "DuckDBReadEngine",
    "PinnedTable",
    "QueryEngineBusyError",
    "QueryError",
    "QueryRejectedError",
    "QueryResult",
    "QueryTimeoutError",
    "ReadEngine",
    "ReadQuery",
]
