"""Fixtures dos testes de interoperabilidade Delta (Polars, delta-rs e DuckDB)."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import polars as pl
import pytest

from tests.support import duckdb_extension_directory

# Schema canônico usado nos testes: cobre os tipos previstos para Silver/Gold.
SCHEMA: dict[str, pl.DataType] = {
    "obs_id": pl.Int64(),
    "territory_code": pl.String(),  # códigos territoriais nunca são numéricos
    "uf": pl.String(),
    "reference_date": pl.Date(),
    "value": pl.Decimal(18, 4),
    "ratio": pl.Float64(),
    "is_estimate": pl.Boolean(),
    "retrieved_at": pl.Datetime("us", "UTC"),
}


def make_frame(ids: list[int], uf: str = "SP", value: str = "1.0000") -> pl.DataFrame:
    """Gera observações determinísticas com o schema canônico."""
    n = len(ids)
    return pl.DataFrame(
        {
            "obs_id": ids,
            "territory_code": [f"35{i:05d}" for i in ids],
            "uf": [uf] * n,
            "reference_date": [date(2022, 7, 1)] * n,
            "value": [Decimal(value)] * n,
            "ratio": [0.5] * n,
            "is_estimate": [False] * n,
            "retrieved_at": [datetime(2026, 1, 1, 12, tzinfo=UTC)] * n,
        },
        schema=SCHEMA,
    )


@pytest.fixture
def table_path(tmp_path: Path) -> str:
    return str(tmp_path / "table")


@pytest.fixture
def duck() -> Iterator[duckdb.DuckDBPyConnection]:
    """Conexão DuckDB em memória, sem auto-instalação nem autoload de extensões."""
    config: dict[str, str | bool | int | float | list[str]] = {
        "autoinstall_known_extensions": False,
        "autoload_known_extensions": False,
    }
    if ext_dir := duckdb_extension_directory():
        config["extension_directory"] = ext_dir
    con = duckdb.connect(config=config)
    try:
        con.execute("LOAD delta")
    except duckdb.Error as exc:  # pragma: no cover - depende do ambiente
        pytest.fail(
            "extensão 'delta' do DuckDB não instalada. Instale com "
            "`uv run python -c \"import duckdb; duckdb.execute('INSTALL delta')\"` "
            f"ou use a imagem Docker do projeto: {exc}"
        )
    yield con
    con.close()
