"""Piloto 2609: seleção nativa sem recompor um Total com pai e filhos."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService
from odb_api.release import ReleaseContext
from odb_modeling.model import build_dim_category
from odb_semantics import SemanticError, load_scope
from odb_semantics.portal import load_portal

ROOT = Path(__file__).resolve().parents[3]


def _service() -> tuple[KpiService, Any, ReleaseContext, dict[str, dict[str, Any]]]:
    catalog = load_scope(ROOT / "configs/indicators", "demografia")
    descriptor = json.loads((ROOT / "configs/catalog/descritores/t2609.json").read_text())
    ages = next(c for c in descriptor["Classificacoes"] if str(c["Id"]) == "240")
    names = {f"c240:{c['Id']}": c["Nome"] for c in ages["Categorias"]}
    rows = build_dim_category(catalog, ["c240"], names).to_dicts()
    categories = {c["category_key"]: c for c in rows}
    gold = SimpleNamespace(
        categories=lambda _ctx: categories,
        partition_categories=lambda _ctx, cid, pid: [
            c for c in rows if c["classification_id"] == cid and c["partition_id"] == pid
        ],
        observed_category_keys=lambda _ctx, _indicator, _classification: set(categories),
    )
    portal = load_portal(ROOT / "configs/portal", "demografia")
    service = KpiService(cast(GoldGateway, gold), portal, page_max=1000)
    return (
        service,
        portal.kpi("nascidos_vivos"),
        cast(ReleaseContext, SimpleNamespace(release_id="teste")),
        categories,
    )


def test_idades_simples_sao_aceitas_sem_incluir_o_grupo_pai() -> None:
    service, kpi, ctx, categories = _service()
    keys = [key for key, cat in categories.items() if cat["name"] in {"15 anos", "16 anos"}]
    assert len(keys) == 2
    chosen = service._selection(ctx, kpi, keys)
    assert chosen["c240"] == frozenset(keys)
    dim = next(d for d in kpi.dimensions if d.classification == "c240")
    assert {c["category_key"] for c in service._partition(ctx, dim, chosen)} == set(keys)
    assert len(service._native_categories(ctx, kpi, dim)) == 45


def test_pai_e_filho_sao_recusados_antes_da_consulta_de_soma() -> None:
    service, kpi, ctx, categories = _service()
    key = next(key for key, cat in categories.items() if cat["name"] == "15 anos")
    parent = categories[key]["parent_category_key"]
    with pytest.raises(SemanticError, match="pai e filho"):
        service._selection(ctx, kpi, [parent, key])


def test_categoria_sem_observacao_no_indicador_nao_e_liberada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, kpi, ctx, categories = _service()
    key = next(key for key, cat in categories.items() if cat["name"] == "15 anos")
    monkeypatch.setattr(
        service._gold, "observed_category_keys", lambda *_args: set(categories) - {key}
    )
    with pytest.raises(SemanticError, match="fora das dimensões"):
        service._selection(ctx, kpi, [key])


def test_sem_filtro_preserva_o_total_e_a_particao_curada() -> None:
    service, kpi, ctx, _ = _service()
    assert service._selection(ctx, kpi, []) == {}
    dim = next(d for d in kpi.dimensions if d.classification == "c240")
    assert len(service._partition(ctx, dim, None)) == 10
