"""Classificação de valores especiais (§9.4).

Legenda oficial do SIDRA (sidra.ibge.gov.br, consultada em 2026-11-03):

==========  ==========================================================  ================
Símbolo     Significado oficial                                         ``value_status``
==========  ==========================================================  ================
número      valor numérico                                              ``valid``
``0``       zero resultante de cálculo ou arredondamento                ``rounded_zero``
``-``       zero absoluto, não resultante de cálculo ou arredondamento  ``true_zero``
``...``     valor não disponível (ex.: município inexistente no ano)    ``not_available``
``..``      valor não se aplica                                         ``not_applicable``
``X``       valor inibido para não identificar o informante             ``suppressed``
A-Z (≠ X)   faixa de valores, com significado específico da tabela      ``range_code``
outro       não reconhecido                                             ``conversion_error``
==========  ==========================================================  ================

O texto original fica sempre em ``value_raw``. ``value`` só é preenchido para
``valid``, ``rounded_zero`` e ``true_zero``. Ausências **nunca** viram zero.
"""

from __future__ import annotations

from enum import StrEnum

import polars as pl

VALUE_DTYPE = pl.Decimal(38, 6)
_NUMERIC = r"^-?\d+(\.\d+)?$"


class ValueStatus(StrEnum):
    """Estado padronizado de um valor."""

    VALID = "valid"
    ROUNDED_ZERO = "rounded_zero"
    TRUE_ZERO = "true_zero"
    NOT_AVAILABLE = "not_available"
    NOT_APPLICABLE = "not_applicable"
    SUPPRESSED = "suppressed"
    RANGE_CODE = "range_code"
    CONVERSION_ERROR = "conversion_error"


# Estados que representam uma quantidade utilizável em agregações.
QUANTITATIVE = frozenset({ValueStatus.VALID, ValueStatus.ROUNDED_ZERO, ValueStatus.TRUE_ZERO})


def classify_sidra_values(raw: str = "value_raw") -> list[pl.Expr]:
    """Expressões que produzem ``value``, ``value_status`` e ``value_decimals``."""
    col = pl.col(raw).str.strip_chars()
    numeric = col.str.contains(_NUMERIC)
    parsed = col.cast(VALUE_DTYPE, strict=False)
    status = (
        pl.when(numeric & (parsed == 0))
        .then(pl.lit(ValueStatus.ROUNDED_ZERO.value))
        .when(numeric)
        .then(pl.lit(ValueStatus.VALID.value))
        .when(col == "-")
        .then(pl.lit(ValueStatus.TRUE_ZERO.value))
        .when(col == "...")
        .then(pl.lit(ValueStatus.NOT_AVAILABLE.value))
        .when(col == "..")
        .then(pl.lit(ValueStatus.NOT_APPLICABLE.value))
        .when(col == "X")
        .then(pl.lit(ValueStatus.SUPPRESSED.value))
        .when(col.str.contains(r"^[A-WYZ]$"))
        .then(pl.lit(ValueStatus.RANGE_CODE.value))
        .otherwise(pl.lit(ValueStatus.CONVERSION_ERROR.value))
    )
    value = (
        pl.when(numeric)
        .then(parsed)
        .when(col == "-")
        .then(pl.lit(0).cast(VALUE_DTYPE))
        .otherwise(pl.lit(None, dtype=VALUE_DTYPE))
    )
    decimals = (
        pl.when(numeric)
        .then(col.str.extract(r"\.(\d+)$", 1).str.len_chars().fill_null(0).cast(pl.Int8))
        .otherwise(pl.lit(None, dtype=pl.Int8))
    )
    return [value.alias("value"), status.alias("value_status"), decimals.alias("value_decimals")]
