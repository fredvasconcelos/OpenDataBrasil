from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from deltalake import DeltaTable, write_deltalake

from odb_lakehouse.protocol import ProtocolViolationError, validate_schema, validate_table
from tests.contracts.delta_interop.conftest import SCHEMA, make_frame


def test_canonical_schema_accepted() -> None:
    validate_schema(SCHEMA)
    validate_schema({"l": pl.List(pl.Int64), "s": pl.Struct({"a": pl.String})})


@pytest.mark.parametrize(
    "dtype",
    [
        pl.Datetime("us"),
        pl.Datetime("us", "America/Sao_Paulo"),
        pl.Categorical(),
        pl.UInt64(),
        pl.Time(),
        pl.Null(),
        pl.Duration("us"),
        pl.List(pl.Datetime("us")),
        pl.Struct({"ok": pl.Int64, "bad": pl.UInt32}),
        pl.Decimal(76, 2),
    ],
)
def test_out_of_profile_types_rejected(dtype: pl.DataType) -> None:
    with pytest.raises(ProtocolViolationError, match="x:"):
        validate_schema({"x": dtype})


def test_table_with_conservative_protocol_passes(tmp_path: Path) -> None:
    make_frame([1]).write_delta(str(tmp_path))
    report = validate_table(DeltaTable(str(tmp_path)))
    assert (report.min_reader_version, report.min_writer_version) == (1, 2)


def test_table_with_timestamp_ntz_rejected(tmp_path: Path) -> None:
    pl.DataFrame({"t": [datetime(2026, 1, 1)]}).write_delta(str(tmp_path))  # noqa: DTZ001
    with pytest.raises(ProtocolViolationError, match="timestampNtz"):
        validate_table(DeltaTable(str(tmp_path)))


def test_table_with_forbidden_configuration_rejected(tmp_path: Path) -> None:
    frame = pl.DataFrame({"t": [datetime(2026, 1, 1, tzinfo=UTC)]})
    write_deltalake(
        str(tmp_path), frame.to_arrow(), configuration={"delta.enableChangeDataFeed": "true"}
    )
    with pytest.raises(ProtocolViolationError, match=r"delta\.enableChangeDataFeed"):
        validate_table(DeltaTable(str(tmp_path)))
