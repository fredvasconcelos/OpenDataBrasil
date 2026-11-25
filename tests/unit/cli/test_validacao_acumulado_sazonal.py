"""Valida a estratégia proposta de acumular a mesma parte entre anos."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[3] / "infrastructure/scripts/validacao_acumulado_sazonal.py"
SPEC = importlib.util.spec_from_file_location("validacao_acumulado", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def point(code: str, value: int | None, status: str = "valid") -> dict[str, Any]:
    """Representa uma parcela da mesma série, sem misturar categorias."""
    return {"period": code, "value": value, "status": status}


def test_soma_a_mesma_parte_entre_anos_sem_acumular_trimestres_do_mesmo_ano() -> None:
    data = [
        point(f"{year}T{q}", base * q)
        for year, base in [(2023, 10), (2024, 100), (2025, 1000)]
        for q in range(1, 5)
    ]
    rows = MODULE.sum_by_part(
        data, native_grain="trimestre", target_grain="trimestre", start_year=2023, end_year=2025
    )
    assert [r["value"] for r in rows] == ["1110", "2220", "3330", "4440"]
    assert rows[0]["contributors"] == ["2023T1", "2024T1", "2025T1"]
    assert all(r["severity"] is None for r in rows)


def test_trimestre_futuro_ausente_preserva_subtotal_com_alerta_amarelo() -> None:
    rows = MODULE.sum_by_part(
        [point(f"{y}T4", 10) for y in [2023, 2024, 2025]],
        native_grain="trimestre",
        target_grain="trimestre",
        start_year=2023,
        end_year=2026,
    )
    t4 = rows[3]
    assert t4["value"] == "30"
    assert t4["expected"] == 4
    assert t4["with_value"] == 3
    assert t4["missing"] == ["2026T4"]
    assert t4["severity"] == "warning"
    assert rows[0]["value"] is None
    assert rows[0]["severity"] == "danger"


def test_soma_os_meses_publicados_do_trimestre_incompleto() -> None:
    data = [
        point(f"{year}M{m:02d}", 1)
        for year in range(2023, 2027)
        for m in range(1, 4)
        if (year, m) != (2026, 3)
    ]
    t1 = MODULE.sum_by_part(
        data, native_grain="mes", target_grain="trimestre", start_year=2023, end_year=2026
    )[0]
    assert t1["value"] == "11"
    assert t1["with_value"] == 11
    assert t1["expected"] == 12
    assert t1["missing"] == ["2026M03"]
    assert t1["severity"] == "warning"


@pytest.mark.parametrize("status", ["suppressed", "not_applicable", "conversion_error"])
def test_parcela_sigilososa_ou_incompativel_nao_e_omitida_como_lacuna_comum(status: str) -> None:
    rows = MODULE.sum_by_part(
        [point("2023T1", 10), point("2024T1", None, status)],
        native_grain="trimestre",
        target_grain="trimestre",
        start_year=2023,
        end_year=2024,
    )
    assert rows[0]["value"] is None
    assert rows[0]["blocked"] == ["2024T1"]
    assert rows[0]["severity"] == "danger"


def test_zero_verdadeiro_e_valor_negativo_contam_como_parcelas_presentes() -> None:
    rows = MODULE.sum_by_part(
        [point("2023", 0, "true_zero"), point("2024", -2)],
        native_grain="ano",
        target_grain="ano",
        start_year=2023,
        end_year=2024,
    )
    assert rows[0]["value"] == "-2"
    assert rows[0]["with_value"] == 2
    assert rows[0]["severity"] is None


def test_intervalo_inclui_os_anos_intermediarios() -> None:
    rows = MODULE.sum_by_part(
        [point("2023", 1), point("2025", 1)],
        native_grain="ano",
        target_grain="ano",
        start_year=2023,
        end_year=2025,
    )
    assert rows[0]["missing"] == ["2024"]
    assert rows[0]["expected"] == 3
    assert rows[0]["severity"] == "warning"


def test_semestral_nativo_nao_inventa_meses_ou_trimestres() -> None:
    rows = MODULE.sum_by_part(
        [point("2023S1", 10), point("2024S1", 20)],
        native_grain="semestre",
        target_grain="semestre",
        start_year=2023,
        end_year=2024,
    )
    assert rows[0]["value"] == "30"
    with pytest.raises(ValueError, match="não é formado"):
        MODULE.sum_by_part(
            [], native_grain="semestre", target_grain="trimestre", start_year=2023, end_year=2024
        )


def test_periodos_duplicados_e_subtotais_misturados_sao_recusados() -> None:
    with pytest.raises(ValueError, match="duplicado"):
        MODULE.sum_by_part(
            [point("2023T1", 10)] * 2,
            native_grain="trimestre",
            target_grain="trimestre",
            start_year=2023,
            end_year=2023,
        )
    with pytest.raises(ValueError, match="Mistura de grãos"):
        MODULE.sum_by_part(
            [point("2023", 40), point("2023T1", 10)],
            native_grain="trimestre",
            target_grain="ano",
            start_year=2023,
            end_year=2023,
        )


def test_soma_anual_exige_confirmacao_da_variavel_na_fonte() -> None:
    kpi = {"kpi_id": "casamentos", "time_grains": [{"grain": "ano"}]}
    with pytest.raises(ValueError, match="não corresponde"):
        MODULE.capability(kpi, [{"sum_periods": False}])


@pytest.mark.parametrize(
    ("rule", "verdict"),
    [
        ("mean", "comparison_only"),
        ("last", "comparison_only"),
        ("compound", "contiguous_compound_only"),
    ],
)
def test_regra_de_media_ultimo_ou_composicao_nao_autoriza_soma(rule: str, verdict: str) -> None:
    kpi = {
        "kpi_id": "exemplo",
        "label": "Exemplo",
        "time_grains": [{"grain": "mes"}],
        "time_aggregation": rule,
        "dimensions": [],
        "levels": ["brasil"],
        "crossed_levels": [],
        "crossed": [],
    }
    assert MODULE.capability(kpi, [])["verdict"] == verdict
