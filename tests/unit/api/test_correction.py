"""Correção pelo índice de preços (ADR-0020): índice do período e período-base."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from odb_api.kpis import correction_base, index_level
from odb_semantics.portal import CorrectionConfig

# Índice encadeado de 2023M01 a 2024M12: 1% ao mês, a partir de 1.
CHAIN = {
    f"{year}M{month:02d}": Decimal("1.01") ** ((year - 2023) * 12 + month - 1)
    for year in (2023, 2024)
    for month in range(1, 13)
}


def _corr(**kw: object) -> CorrectionConfig:
    return CorrectionConfig(id="ipca", label="IPCA geral", indicator="ipca_x", **kw)  # type: ignore[arg-type]


def test_referencia_por_mes_de_pesquisa() -> None:
    corr = _corr(reference_months={"2023": "2023M01", "2024": "2024M01"})
    assert index_level(corr, CHAIN, "2023") == 1
    assert index_level(corr, CHAIN, "2024") == Decimal("1.01") ** 12
    assert index_level(corr, CHAIN, "2022") is None
    assert correction_base(corr, CHAIN, ["2023", "2024"]) == "2024"


def test_referencia_pelo_proprio_periodo() -> None:
    corr = _corr(reference="period")
    assert index_level(corr, CHAIN, "2024M03") == CHAIN["2024M03"]
    quarter = (CHAIN["2024M04"] + CHAIN["2024M05"] + CHAIN["2024M06"]) / 3
    assert index_level(corr, CHAIN, "2024T2") == quarter
    year = sum((CHAIN[f"2023M{m:02d}"] for m in range(1, 13)), Decimal(0)) / 12
    assert index_level(corr, CHAIN, "2023") == year
    # Ano sem todos os meses no índice: sem valor.
    assert index_level(corr, CHAIN, "2025") is None
    assert index_level(corr, CHAIN, "2022") is None


def test_base_e_o_periodo_mais_recente_coberto() -> None:
    corr = _corr(reference="period")
    assert correction_base(corr, CHAIN, ["2022", "2023", "2024", "2025"]) == "2024"
    assert correction_base(corr, CHAIN, ["2024M11", "2024M12", "2025M01"]) == "2024M12"
    assert correction_base(corr, CHAIN, ["2010"]) is None


def test_fator_anual_e_a_razao_das_medias() -> None:
    corr = _corr(reference="period")
    start, end = index_level(corr, CHAIN, "2023"), index_level(corr, CHAIN, "2024")
    assert start is not None
    assert end is not None
    # Com 1% ao mês, a média de 2024 é a de 2023 vezes 1,01¹².
    assert end / start == pytest.approx(Decimal("1.01") ** 12)


def test_meses_de_referencia_obrigatorios_no_modo_months() -> None:
    with pytest.raises(ValidationError, match="reference_months"):
        _corr()
