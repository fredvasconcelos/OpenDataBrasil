"""Fragmento curado da POF em série (2309, 1594, 6715; ADR-0016), com fixtures reais no Brasil."""

from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl

from odb_semantics import load_catalog
from tests.gold_support import ALL_DATASETS, REPO_INDICATORS, SOURCE_FRAGMENTS, GoldEnv
from tests.ingestion_support import TEST_SOURCES


def test_expense_hierarchy_from_descriptor_reaches_gold(tmp_path: Path) -> None:
    catalog = load_catalog(
        REPO_INDICATORS / "demografia.toml", [REPO_INDICATORS / "demografia" / "pof.toml"]
    )
    sources = tmp_path / "sources"
    sources.mkdir()
    shutil.copy(TEST_SOURCES / "ibge-test.toml", sources)
    shutil.copy(SOURCE_FRAGMENTS / "ibge-6715.toml", sources)  # fragmento sem instituição
    env = GoldEnv(tmp_path, catalog, sources_dir=sources)
    env.prepare([*ALL_DATASETS, "ibge-sidra-2309", "ibge-sidra-1594", "ibge-sidra-6715"])
    build = env.gold.build()
    failed = [c.check_id for c in build.checks if c.status.value == "fail"]
    assert build.status == "succeeded", (build.error, failed)
    fact = pl.read_delta(build.tables["fact_pof_household_expense"].storage_uri)
    # 2008 e 2018: 8 classes (com o Total) x 93 tipos; 2002: só o Total x 89 tipos.
    assert fact.group_by("period").len().sort("period").rows() == [
        ("2002", 89),
        ("2008", 744),
        ("2018", 744),
    ]
    total = fact.filter(
        (pl.col("income_class_category_key") == "c339:7999")
        & (pl.col("expense_type_category_key") == "c12190:103536")
    ).sort("period")
    # Despesa total média mensal familiar no Brasil (R$ da época), das tabelas oficiais.
    assert [float(v) for v in total["average_expense"]][:2] == [1778.03, 2626.31]
    assert total["period"].to_list() == ["2002", "2008", "2018"]
    assert all(float(v) == 100.0 for v in total["expense_share_pct"])
    # 2002 entra no Total da c339 (a 2309 não tem a classificação); as faixas são de 2008/2018.
    classes = fact.group_by("period").agg(pl.col("income_class_category_key").n_unique())
    assert dict(classes.rows()) == {"2002": 1, "2008": 8, "2018": 8}
    obs = pl.read_delta(build.tables["indicator_observation"].storage_uri).filter(
        pl.col("indicator_id") == "despesa_familiar"
    )
    assert sorted(set(obs["source_table_id"].to_list())) == ["1594", "2309", "6715"]
    indicator = (
        pl.read_delta(build.tables["dim_indicator"].storage_uri)
        .filter(pl.col("indicator_id") == "despesa_familiar")
        .row(0, named=True)
    )
    assert indicator["dataset_id"] == "ibge-pof-despesa-familiar"
    assert indicator["source_table_id"] == "6715"  # a edição mais recente
    cats = pl.read_delta(build.tables["dim_category"].storage_uri).filter(
        pl.col("classification_id") == "c12190"
    )
    assert cats.height == 93 + 18  # as 18 categorias próprias da POF 2002-2003
    food = cats.filter(pl.col("category_id") == "103539").row(0, named=True)
    assert food["name"] == "2.1.1 Alimentação"
    assert food["parent_category_key"] == "c12190:103538"  # 2.1 Despesas de consumo
    assert food["partition_id"] == "d2_1_despesas_de_consumo"
    assert food["depth"] == 3  # Total > 2 > 2.1 > 2.1.1
