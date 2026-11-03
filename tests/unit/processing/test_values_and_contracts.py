from decimal import Decimal

import polars as pl
import pytest

from odb_processing.contracts import (
    DTB_MUNICIPALITY,
    SIDRA_OBSERVATION,
    SchemaChange,
    compare_schema,
)
from odb_processing.values import classify_sidra_values


@pytest.mark.parametrize(
    ("raw", "value", "status", "decimals"),
    [
        ("1751950", Decimal("1751950"), "valid", 0),
        ("7067.127", Decimal("7067.127"), "valid", 3),
        ("-12.5", Decimal("-12.5"), "valid", 1),
        ("0", Decimal(0), "rounded_zero", 0),
        ("0.00", Decimal(0), "rounded_zero", 2),
        ("-", Decimal(0), "true_zero", None),
        ("...", None, "not_available", None),
        ("..", None, "not_applicable", None),
        ("X", None, "suppressed", None),
        ("A", None, "range_code", None),
        ("?", None, "conversion_error", None),
        ("1,5", None, "conversion_error", None),
        (" 42 ", Decimal(42), "valid", 0),
    ],
)
def test_sidra_value_legend(
    raw: str, value: Decimal | None, status: str, decimals: int | None
) -> None:
    row = pl.DataFrame({"value_raw": [raw]}).select(*classify_sidra_values()).row(0)
    assert row == (value, status, decimals)


def test_missing_values_never_become_zero() -> None:
    frame = pl.DataFrame({"value_raw": ["...", "..", "X", "A"]}).select(*classify_sidra_values())
    assert frame["value"].null_count() == 4


def test_schema_comparison() -> None:
    schema = SIDRA_OBSERVATION.frame_schema()
    assert compare_schema(schema, SIDRA_OBSERVATION).change is SchemaChange.IDENTICAL
    fewer = pl.Schema({k: v for k, v in schema.items() if k != "value_decimals"})
    addition = compare_schema(fewer, SIDRA_OBSERVATION)
    assert addition.change is SchemaChange.COMPATIBLE_ADDITION
    assert "value_decimals" in addition.details[0]
    extra = pl.Schema({**schema, "legacy": pl.String()})
    assert compare_schema(extra, SIDRA_OBSERVATION).change is SchemaChange.INCOMPATIBLE
    retyped = pl.Schema({**schema, "value": pl.Float64()})
    result = compare_schema(retyped, SIDRA_OBSERVATION)
    assert result.change is SchemaChange.INCOMPATIBLE
    assert "tipos alterados" in result.details[0]
    assert set(DTB_MUNICIPALITY.key) <= set(DTB_MUNICIPALITY.schema)
