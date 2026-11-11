"""Fragmento curado da POF (6715) na Gold, com fixtures reais no nível Brasil."""

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
    env.prepare([*ALL_DATASETS, "ibge-sidra-6715"])
    build = env.gold.build()
    failed = [c.check_id for c in build.checks if c.status.value == "fail"]
    assert build.status == "succeeded", (build.error, failed)
    fact = pl.read_delta(build.tables["fact_pof_household_expense"].storage_uri)
    # 8 classes (com o Total) x 93 tipos de despesa, no Brasil.
    assert fact.height == 744
    total = fact.filter(
        (pl.col("income_class_category_key") == "c339:7999")
        & (pl.col("expense_type_category_key") == "c12190:103536")
    )
    assert total["average_expense"].to_list() == [total["average_expense"][0]]
    assert float(total["expense_share_pct"][0]) == 100.0
    cats = pl.read_delta(build.tables["dim_category"].storage_uri).filter(
        pl.col("classification_id") == "c12190"
    )
    assert cats.height == 93
    food = cats.filter(pl.col("category_id") == "103539").row(0, named=True)
    assert food["name"] == "2.1.1 Alimentação"
    assert food["parent_category_key"] == "c12190:103538"  # 2.1 Despesas de consumo
    assert food["partition_id"] == "d2_1_despesas_de_consumo"
    assert food["depth"] == 3  # Total > 2 > 2.1 > 2.1.1
