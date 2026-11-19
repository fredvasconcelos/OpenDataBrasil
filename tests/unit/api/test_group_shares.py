"""Percentuais por hierarquia, com valores sintéticos em categorias oficiais da POF."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pytest
from pydantic import ValidationError

from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService, Observation
from odb_api.release import ReleaseContext
from odb_api.schemas import DetailOut, GeographyRefOut, Provenance
from odb_semantics.portal import (
    DimensionConfig,
    KpiConfig,
    ShortLabels,
    allows_category_shares,
    dimension_share_basis,
)

INCOME = ("c339:47558", "c339:47559", "c339:47560")
EXPENSE = ("c12190:103539", "c12190:103540", "c12190:103554")
IT, ET, GROUP = "c339:7999", "c12190:103536", "c12190:103538"


class FixtureGold:
    """Metadados mínimos sem banco, fonte remota ou escrita de dados."""

    def indicators(self, _ctx: ReleaseContext) -> dict[str, Any]:
        return {"despesa_familiar": {"unit": "Reais", "additivity": "non_additive", "caveats": []}}

    def categories(self, _ctx: ReleaseContext) -> dict[str, Any]:
        return {
            key: {"name": key, "category_key": key} for key in (*INCOME, *EXPENSE, IT, ET, GROUP)
        }

    def total_category(self, _ctx: ReleaseContext, dim: str) -> dict[str, str]:
        return {"category_key": IT if dim == "c339" else ET}

    def partition_categories(self, _ctx: ReleaseContext, dim: str, _partition: str) -> list[Any]:
        return [{"category_key": key} for key in (INCOME if dim == "c339" else EXPENSE)]


def detail(
    dims: list[str], *, missing: bool = False, zero: bool = False, negative: bool = False
) -> DetailOut:
    """Monta o exemplo25/70/5 sem confundir médias com participação ponderada."""
    service = object.__new__(KpiService)
    service._gold = cast(GoldGateway, FixtureGold())
    service._short = ShortLabels()
    kpi = KpiConfig(
        id="despesa_familiar",
        label="Despesa média",
        indicator="despesa_familiar",
        dimensions=(
            DimensionConfig(
                classification="c339",
                partition="classes_rendimento",
                label="Renda",
                share_basis="displayed_sum",
            ),
            DimensionConfig(
                classification="c12190",
                partition="d2_1_despesas_de_consumo",
                label="Consumo",
                share_basis="published_group",
                share_base_category=GROUP,
            ),
        ),
    )
    records: dict[tuple[str, str], Decimal | None] = {
        (IT, ET): Decimal(999),
        (IT, GROUP): Decimal(600),
    }
    records.update(
        {
            (IT, category): Decimal(value)
            for category, value in zip(EXPENSE, [120, 360, 120], strict=True)
        }
    )
    for income, value, parts in zip(
        INCOME, [250, 700, 50], [[30, 60, 10], [10, 20, 70], [20, 60, 20]], strict=True
    ):
        records[(income, ET)] = Decimal(0 if zero else value)
        subtotal = Decimal(value) * Decimal("0.6")
        records[(income, GROUP)] = subtotal
        for category, part in zip(EXPENSE, parts, strict=True):
            records[(income, category)] = subtotal * Decimal(part) / 100
    if missing:
        records[(INCOME[0], ET)] = None
    if negative:
        records[(INCOME[0], ET)] = Decimal(-1)
    obs = [
        Observation(
            "uf:25", "Paraíba", "2018", combo, value, "suppressed" if value is None else "valid"
        )
        for combo, value in records.items()
    ]
    if dims == ["c339"]:
        obs = [replace(row, combo=(row.combo[0],)) for row in obs if row.combo[1] == ET]
    elif dims == ["c12190"]:
        obs = [replace(row, combo=(row.combo[1],)) for row in obs if row.combo[0] == IT]
    return service._detail_out(
        cast(ReleaseContext, object()),
        kpi,
        ref=GeographyRefOut(geography_key="uf:25", name="Paraíba", level_id="uf"),
        chosen="2018",
        window=[],
        dims=dims,
        sel={},
        obs=obs,
        prov=Provenance(release_id="teste", tables=[], derived=False, truncated=False),
    )


def test_n1_composto_dos_valores_exibidos_preserva_total_oficial() -> None:
    root = detail(["c339"]).root
    assert root.value == 999
    assert root.share_pct is None  # Não rotula999 como100% de1000.
    assert root.children_share_base_value == 1000
    assert [child.share_pct for child in root.children] == [25, 70, 5]


def test_n2_usa_subtotal_publicado_em_vez_da_despesa_familiar_total() -> None:
    root = detail(["c12190"]).root
    assert root.value == 999
    assert root.children_share_base_value == 600
    assert [child.share_pct for child in root.children] == [20, 60, 20]


def test_n1_global_e_n2_dentro_de_cada_classe() -> None:
    root = detail(["c339", "c12190"]).root
    assert [child.share_pct for child in root.children] == [25, 70, 5]
    assert [[n.share_pct for n in c.children] for c in root.children] == [
        [30, 60, 10],
        [10, 20, 70],
        [20, 60, 20],
    ]
    assert [c.children_share_base_value for c in root.children] == [150, 420, 30]


@pytest.mark.parametrize("option", [{"missing": True}, {"zero": True}, {"negative": True}])
def test_base_zero_ou_sigilo_nao_inventa_percentual(option: dict[str, bool]) -> None:
    root = detail(["c339"], **option).root
    assert all(child.share_pct is None for child in root.children)


def test_composicao_de_media_nao_autoriza_soma_nos_filtros() -> None:
    dim = DimensionConfig(classification="c339", partition="classes_rendimento", label="Renda")
    assert dimension_share_basis("Reais", "non_additive", dim) == "displayed_sum"
    assert not allows_category_shares("Reais", "non_additive")
    assert dimension_share_basis("Pessoas", "additive", dim) == "published_total"


def test_serie_reutiliza_subtotal_do_mapa_por_periodo() -> None:
    service = object.__new__(KpiService)
    service._gold = cast(GoldGateway, FixtureGold())
    service._short = ShortLabels()
    kpi = KpiConfig(
        id="despesa_familiar",
        label="Despesa média",
        indicator="despesa_familiar",
        dimensions=(
            DimensionConfig(
                classification="c12190",
                partition="consumo",
                label="Consumo",
                share_basis="published_group",
                share_base_category=GROUP,
            ),
        ),
    )
    observations = [
        Observation("uf:25", "Paraíba", period, (category,), Decimal(value), "valid")
        for period, factor in [("2008", 1), ("2018", 2)]
        for category, value in [
            (ET, 999 * factor),
            (GROUP, 300 * factor),
            (EXPENSE[0], 60 * factor),
        ]
    ]
    shares = service._series_shares(
        cast(ReleaseContext, object()),
        kpi,
        ref=GeographyRefOut(geography_key="uf:25", name="Paraíba", level_id="uf"),
        dims=["c12190"],
        selected={},
        observations=observations,
        prov=Provenance(release_id="teste", tables=[], derived=False, truncated=False),
    )
    assert shares[((EXPENSE[0],), "2008")] == (20, 300)
    assert shares[((EXPENSE[0],), "2018")] == (20, 600)
    assert shares[((ET,), "2018")] == (None, 600)


@pytest.mark.parametrize(
    "fields",
    [
        {"share_basis": "published_group"},
        {"share_basis": "displayed_sum", "share_base_category": GROUP},
        {"share_basis": "published_group", "share_base_category": IT},
    ],
)
def test_referencia_do_grupo_exige_base_da_mesma_classificacao(fields: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        DimensionConfig.model_validate(
            {"classification": "c12190", "partition": "consumo", "label": "Consumo", **fields}
        )
