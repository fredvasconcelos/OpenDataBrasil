"""Integra o operador sazonal à consulta sem permitir soma de estoques."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService, Observation
from odb_api.release import ReleaseContext
from odb_api.schemas import GeographyRefOut, Provenance
from odb_semantics import SemanticError
from odb_semantics.portal import PortalConfig, TemporalSumPolicy


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> tuple[KpiService, Any, ReleaseContext]:
    portal = PortalConfig.model_validate(
        {
            "config_version": "1",
            "scope": "demografia",
            "themes": [
                {
                    "id": "civil",
                    "label": "Registro civil",
                    "subthemes": [
                        {
                            "id": "obitos",
                            "label": "Óbitos",
                            "kpis": [
                                {
                                    "id": "obitos_mensal",
                                    "label": "Óbitos por mês",
                                    "indicator": "obitos_mensal",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )
    gold = MagicMock(spec=GoldGateway)
    gold.indicators.return_value = {
        "obitos_mensal": {
            "time_grains": ["mes", "trimestre", "semestre", "ano"],
            "time_aggregation": "sum",
            "periods": ["2023M01", "2024M01", "2024M02"],
            "source_variable_id": "343",
            "unit": "Pessoas",
            "caveats": [],
        }
    }
    svc = KpiService(gold, portal, page_max=100)
    monkeypatch.setattr(svc, "kpi", lambda _ctx, _id: portal.kpis()[0])
    monkeypatch.setattr(
        svc,
        "_ref",
        lambda _ctx, _key: GeographyRefOut(
            geography_key="brasil:1", name="Brasil", level_id="brasil"
        ),
    )
    return svc, gold, cast(ReleaseContext, object())


def test_le_as_parcelas_nativas_e_preserva_meses_do_trimestre_incompleto(
    service: tuple[KpiService, Any, ReleaseContext],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, _, ctx = service
    rows = [
        Observation("brasil:1", "Brasil", code, (), Decimal(value), "valid", "2654")
        for code, value in [("2023M01", 10), ("2024M01", 100), ("2024M02", 200)]
    ]
    read = MagicMock(return_value=(rows, Provenance(release_id="teste", tables=[], derived=False)))
    monkeypatch.setattr(svc, "_observations", read)
    out = svc.seasonal(
        ctx,
        "obitos_mensal",
        geography="brasil:1",
        dimensions=[],
        year_from=2023,
        year_to=2024,
        grain="trimestre",
    )
    assert out.series[0].points[0].value == 310
    assert out.series[0].points[0].severity == "warning"
    assert out.series[0].points[0].expected == 6
    assert out.series[0].points[0].present == 3
    assert out.series[0].points[1].value is None
    assert out.series[0].points[1].severity == "danger"
    assert read.call_args.kwargs.get("grain") is None
    assert "2024M02" in read.call_args.kwargs["periods"]
    assert out.provenance.derived


def test_truncamento_nao_vira_subtotal_parcial_valido(
    service: tuple[KpiService, Any, ReleaseContext],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, _, ctx = service
    monkeypatch.setattr(
        svc,
        "_observations",
        MagicMock(
            return_value=(
                [],
                Provenance(release_id="teste", tables=[], derived=False, truncated=True),
            )
        ),
    )
    with pytest.raises(SemanticError, match="truncado"):
        svc.seasonal(
            ctx, "obitos_mensal", geography="brasil:1", dimensions=[], year_from=2023, year_to=2024
        )


def test_media_pode_isolar_mas_nao_soma_entre_anos(
    service: tuple[KpiService, Any, ReleaseContext],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, gold, ctx = service
    gold.indicators.return_value["obitos_mensal"]["time_aggregation"] = "mean"
    read = MagicMock()
    monkeypatch.setattr(svc, "_observations", read)
    assert svc._temporal(ctx, svc._portal.kpis()[0]).isolate
    with pytest.raises(SemanticError, match="não autorizada"):
        svc.seasonal(
            ctx, "obitos_mensal", geography="brasil:1", dimensions=[], year_from=2023, year_to=2024
        )
    read.assert_not_called()


def test_politica_anual_exige_a_mesma_tabela_e_variavel(
    service: tuple[KpiService, Any, ReleaseContext],
) -> None:
    svc, gold, ctx = service
    svc._portal = svc._portal.model_copy(update={"temporal_sums": ()})
    # A fonte declarada na política é sinteticamente associada à fixture para
    # conferir a guarda de linhagem; não é uma permissão real para esse KPI.
    policy = TemporalSumPolicy(kpi="obitos_mensal", table="2654", variable="343", note="Teste")
    svc._portal = svc._portal.model_copy(update={"temporal_sums": (policy,)})
    meta = gold.indicators.return_value["obitos_mensal"]
    meta.update(time_aggregation=None, time_grains=["ano"], periods=["2023", "2024"])
    gold.coverage.return_value = {"obitos_mensal": {"2654": {}}}
    assert svc._temporal(ctx, svc._portal.kpis()[0]).seasonal_sum
    meta["source_variable_id"] = "1000343"
    assert not svc._temporal(ctx, svc._portal.kpis()[0]).seasonal_sum
    meta["source_variable_id"] = "343"
    gold.coverage.return_value = {"obitos_mensal": {"2654": {}, "2609": {}}}
    assert not svc._temporal(ctx, svc._portal.kpis()[0]).seasonal_sum
