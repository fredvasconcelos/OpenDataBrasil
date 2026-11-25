"""Soma sazonal sem inventar valores, ocultar sigilo ou repetir categorias."""

from __future__ import annotations

from decimal import Decimal

import pytest

from odb_semantics.periods import PeriodError
from odb_semantics.seasonal import SeasonalInput, seasonal_groups, seasonal_sum


def test_soma_a_mesma_parte_com_parcelas_conhecidas_e_alerta() -> None:
    points = [
        SeasonalInput(f"{y}T1", Decimal(n), "valid")
        for y, n in [(2023, 10), (2024, 100), (2025, 1000)]
    ]
    values = seasonal_sum(points, native="trimestre", target="trimestre", start=2023, end=2026)
    assert values[0].value == 1110
    assert values[0].status == "partial_sum"
    assert values[0].missing == ("2026T1",)
    assert (values[0].present, values[0].expected) == (3, 4)
    assert values[1].value is None
    assert values[1].status == "absent"


def test_meses_conhecidos_nao_somem_do_trimestre_incompleto() -> None:
    points = [
        SeasonalInput(f"{y}M{m:02d}", Decimal(1), "valid")
        for y in [2023, 2024]
        for m in [1, 2, 3]
        if (y, m) != (2024, 3)
    ]
    t1 = seasonal_sum(points, native="mes", target="trimestre", start=2023, end=2024)[0]
    assert t1.value == 5
    assert t1.expected == 6
    assert t1.missing == ("2024M03",)


@pytest.mark.parametrize("status", ["suppressed", "not_applicable", "conversion_error"])
def test_sigilo_erro_e_nao_aplicavel_bloqueiam_sem_perder_motivo(status: str) -> None:
    points = [SeasonalInput("2023", Decimal(10), "valid"), SeasonalInput("2024", None, status)]
    value = seasonal_sum(points, native="ano", target="ano", start=2023, end=2024)[0]
    assert value.value is None
    assert value.blocked == ("2024",)
    assert value.status == "blocked_accumulation"


def test_zero_e_negativo_sao_parcelas_validas_e_parcial_territorial_nao_e_ocultado() -> None:
    value = seasonal_sum(
        [
            SeasonalInput("2023", Decimal(0), "true_zero"),
            SeasonalInput("2024", Decimal(-2), "partial_sum"),
        ],
        native="ano",
        target="ano",
        start=2023,
        end=2024,
    )[0]
    assert value.value == -2
    assert value.present == 2
    assert value.input_partial == ("2024",)
    assert value.status == "partial_sum"


def test_duplicidade_frequencia_inventada_e_intervalo_excessivo_sao_recusados() -> None:
    with pytest.raises(PeriodError, match="duplicada"):
        seasonal_sum(
            [SeasonalInput("2023", Decimal(1), "valid")] * 2,
            native="ano",
            target="ano",
            start=2023,
            end=2023,
        )
    with pytest.raises(PeriodError, match="120 parcelas"):
        seasonal_groups("mes", "trimestre", 2000, 2025)
    with pytest.raises(PeriodError, match="não é formado"):
        seasonal_groups("semestre", "mes", 2023, 2024)
    assert len(seasonal_groups("semestre", "semestre", 2023, 2024)) == 2
