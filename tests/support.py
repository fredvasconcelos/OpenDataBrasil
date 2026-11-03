"""Utilitários compartilhados pelos testes."""

import os

EXTENSION_DIR_ENV = "ODB_DUCKDB_EXTENSION_DIRECTORY"


def duckdb_extension_directory() -> str | None:
    """Diretório de extensões DuckDB do ambiente: imagem Docker ou padrão do usuário."""
    return os.environ.get(EXTENSION_DIR_ENV) or None
