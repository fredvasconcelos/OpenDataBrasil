from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from deltalake import DeltaTable

from odb_lakehouse import DeltaReader
from odb_modeling import model
from odb_modeling.builder import GoldBuilder
from odb_modeling.geography import GeographyError, build_ancestor_bridge, build_dim_geography
from odb_modeling.quality import category_reconciliation
from odb_processing.quality import CheckStatus
from odb_semantics import load_catalog
from tests.gold_support import REPO_INDICATORS, GoldEnv

BASE = (REPO_INDICATORS / "demografia.toml").read_text(encoding="utf-8")


@pytest.fixture
def env(tmp_path: Path) -> GoldEnv:
    gold = GoldEnv(tmp_path)
    gold.prepare()
    return gold


def _read(build_table: object) -> pl.DataFrame:
    table = build_table
    return DeltaReader().scan(table.storage_uri, table.delta_version).collect()  # type: ignore[attr-defined]


def test_build_tables_hierarchies_and_lineage(env: GoldEnv) -> None:
    build = env.gold.build()
    assert build.status == "succeeded", build.error
    assert not [c for c in build.checks if c.status is CheckStatus.FAIL]
    assert set(build.tables) == set(env.gold.contracts())
    for table in build.tables.values():
        assert table.storage_uri.startswith(env.layout.root_uri + "/gold/demografia/")
        assert DeltaTable(table.storage_uri).protocol().min_writer_version == 2

    obs = _read(build.tables["indicator_observation"])
    assert obs.height == 7548
    stored = {a.artifact_id for a in env.ingestion.by_status("stored")}
    assert set(obs["bronze_artifact_id"].unique().to_list()) <= stored
    assert obs["gold_build_id"].unique().to_list() == [build.build_id]

    geo = _read(build.tables["dim_geography"])
    counts = dict(geo.group_by("level_id").len().iter_rows())
    assert counts["municipio"] == 5571
    assert counts["uf"] == 27
    assert counts["regiao"] == 5
    bridge = _read(build.tables["bridge_geography_ancestor"])
    cuiaba = bridge.filter(pl.col("geography_key") == "municipio:5103403").sort("distance")
    assert cuiaba["ancestor_level"].to_list() == [
        "municipio",
        "regiao_imediata",
        "regiao_intermediaria",
        "uf",
        "regiao",
        "brasil",
    ]
    assert cuiaba["ancestor_key"][3] == "uf:51"

    fact = _read(build.tables["fact_indigenous_population"])
    brasil = fact.filter(
        (pl.col("geography_key") == "brasil:1")
        & (pl.col("declaration_category_key") == "c1714:60024")
        & (pl.col("location_category_key") == "c2661:32776")
    ).row(0, named=True)
    assert brasil["indigenous_persons"] == Decimal("1694836")
    assert brasil["population"] == Decimal("203080756")
    assert brasil["indigenous_share_pct"] == Decimal("0.83")
    estimate = _read(build.tables["fact_population_estimate"])
    assert "pending_installation" in estimate.columns
    assert not estimate["pending_installation"].any()  # fixtures sem nível municipal

    checks = {c.check_id: c for c in build.checks}
    race = checks["reconciliation.category.censo_populacao_cor_raca.c86.cor_ou_raca"]
    assert race.status is CheckStatus.PASS
    assert {r["period"]: r["residual"] for r in race.details["residual_brasil"]} == {
        "2010": "6608.000000",
        "2022": "11119.000000",
    }
    assert checks["notes.pending_installation"].status is CheckStatus.PASS


def test_skip_force_and_versions(env: GoldEnv) -> None:
    first = env.gold.build()
    again = env.gold.build()
    assert again.status == "skipped"
    assert again.tables == first.tables
    forced = env.gold.build(force=True)
    assert forced.status == "succeeded"
    assert {t.delta_version for t in forced.tables.values()} == {1}


def test_undeclared_category_blocks_everything(env: GoldEnv, tmp_path: Path) -> None:
    path = tmp_path / "demografia.toml"
    path.write_text(
        BASE.replace(
            'categories = ["2776", "2777", "2778", "2779", "2780"]',
            'categories = ["2776", "2777", "2778", "2779"]',
        ),
        encoding="utf-8",
    )
    builder = GoldBuilder(
        env.sources, load_catalog(path), env.layout, env.writer, env.registry, code_version="t"
    )
    build = builder.build()
    assert build.status == "failed"
    assert "semantics.category_hierarchy" in (build.error or "")
    failed = {c.check_id: c for c in build.checks}["semantics.category_hierarchy"]
    assert failed.observed == {"c86": ["2780"]}
    assert not build.tables
    assert not DeltaTable.is_deltatable(env.gold.table_uri("indicator_observation"))


def test_missing_silver_fails_before_reading(tmp_path: Path) -> None:
    env = GoldEnv(tmp_path)
    build = env.gold.build()
    assert build.status == "failed"
    assert "Silver sem execução válida" in (build.error or "")


def test_incompatible_existing_schema_blocks_writes(env: GoldEnv) -> None:
    uri = env.gold.table_uri("dim_period")
    pl.DataFrame({"period": [1]}).write_delta(uri)
    build = env.gold.build()
    assert build.status == "failed"
    assert "dim_period: mudança de schema incompatível" in (build.error or "")
    assert not DeltaTable.is_deltatable(env.gold.table_uri("dim_geography"))


def _silver_rows(names: list[tuple[str, str]]) -> pl.DataFrame:
    """Linhas SINTÉTICAS (códigos fictícios) no formato da Silver."""
    return pl.DataFrame(
        {
            "table_id": ["6579"] * len(names),
            "period": ["2004"] * len(names),
            "territorial_level": ["6"] * len(names),
            "territory_id": [code for code, _ in names],
            "territory_name": [name for _, name in names],
        }
    )


def test_pending_installation_resolution() -> None:
    catalog = load_catalog(REPO_INDICATORS / "demografia.toml")
    datasets = {d: model.DatasetInfo(d, d.rsplit("-", 1)[1], None, "x") for d in catalog.datasets()}
    silver = _silver_rows(
        [
            ("2299901", "Aroeiras do Itaim - PI"),
            ("5099902", "Figueirão - MS"),
            ("5199903", "Ipiranga do Norte - MT"),
            ("5199904", "Itanhangá - MT"),
        ]
    )
    resolved, report = model.resolve_pending_installation(catalog, silver, datasets)
    assert resolved[("ibge-sidra-6579", "2004")] == {"2299901", "5099902", "5199903", "5199904"}
    assert [r["applied"] for r in report] == [True, False, False]

    partial = _silver_rows([("2299901", "Aroeiras do Itaim - PI")])
    _, problems = model.resolve_pending_installation(catalog, partial, datasets)
    assert [r["municipality"] for r in problems if r.get("problem")] == [
        "Figueirão - MS",
        "Ipiranga do Norte - MT",
        "Itanhangá - MT",
    ]
    assert model.uf_abbreviations(silver) == {"22": "PI", "50": "MS", "51": "MT"}


def _dtb(rows: list[tuple[str, str, str]]) -> pl.DataFrame:
    """(município, região imediata, região intermediária) na UF 29."""
    return pl.DataFrame(
        {
            "region_id": ["2"] * len(rows),
            "region_name": ["Nordeste"] * len(rows),
            "uf_id": ["29"] * len(rows),
            "uf_name": ["Bahia"] * len(rows),
            "intermediate_region_id": [r[2] for r in rows],
            "intermediate_region_name": ["Inter"] * len(rows),
            "immediate_region_id": [r[1] for r in rows],
            "immediate_region_name": ["Imed"] * len(rows),
            "municipality_id": [r[0] for r in rows],
            "municipality_name": ["Mun"] * len(rows),
        }
    )


def test_geography_orphans_and_inconsistent_reference() -> None:
    dtb = _dtb([("2927408", "290001", "2901")])
    observed = pl.DataFrame(
        {"level_id": ["municipio"], "code": ["2999999"], "name": ["Extinto - BA"]}
    )
    geo = build_dim_geography(dtb, observed, reference="teste", uf_abbreviations={"29": "BA"})
    orphan = geo.filter(pl.col("geography_key") == "municipio:2999999").row(0, named=True)
    assert orphan["in_reference"] is False
    assert orphan["parent_key"] == "uf:29"
    assert orphan["uf_abbreviation"] == "BA"
    bridge = build_ancestor_bridge(geo)
    assert bridge.filter(pl.col("geography_key") == "municipio:2999999")[
        "ancestor_key"
    ].to_list() == ["municipio:2999999", "uf:29", "regiao:2", "brasil:1"]

    with pytest.raises(GeographyError, match="mais de um pai"):
        build_dim_geography(
            _dtb([("2927408", "290001", "2901"), ("2900108", "290001", "2902")]),
            observed.clear(),
            reference="teste",
            uf_abbreviations={},
        )


def test_special_levels_have_two_ancestors(env: GoldEnv) -> None:
    build = env.gold.build()
    geo = _read(build.tables["dim_geography"])
    counts = dict(geo.group_by("level_id").len().iter_rows())
    assert counts["territorio_quilombola"] == 495
    assert counts["territorio_quilombola_uf"] == 503
    assert counts["amazonia_legal_uf"] == 9
    part = geo.filter(pl.col("geography_key") == "territorio_quilombola_uf:21003").row(
        0, named=True
    )
    assert part["parent_key"] == "uf:21"
    assert part["name"] == "Itamoari - MA"
    bridge = _read(build.tables["bridge_geography_ancestor"])
    ancestors = set(
        bridge.filter(pl.col("geography_key") == "territorio_quilombola_uf:21003")["ancestor_key"]
    )
    assert ancestors == {
        "territorio_quilombola_uf:21003",
        "territorio_quilombola:3",
        "uf:21",
        "regiao:2",
        "brasil:1",
    }
    # Itamoari atravessa PA e MA: as duas partes têm o mesmo território como ancestral.
    parts = bridge.filter(pl.col("ancestor_key") == "territorio_quilombola:3")["geography_key"]
    assert sorted(parts.to_list()) == [
        "territorio_quilombola:3",
        "territorio_quilombola_uf:15003",
        "territorio_quilombola_uf:21003",
    ]
    checks = {c.check_id: c.status for c in build.checks}
    assert checks["geography.reference"] is CheckStatus.PASS


def test_category_reconciliation_flags_exhaustive_divergence() -> None:
    catalog = load_catalog(REPO_INDICATORS / "demografia.toml")
    rows = [
        ("c2661:32776", "100"),
        ("c2661:60027", "30"),
        ("c2661:60028", "60"),  # 30 + 60 != 100
    ]
    obs = pl.DataFrame(
        {
            "indicator_id": ["censo_pessoas_quilombolas"] * 3,
            "geography_key": ["uf:29"] * 3,
            "period": ["2022"] * 3,
            "breakdown_key": [k for k, _ in rows],
            "value": [Decimal(v) for _, v in rows],
            "value_status": ["valid"] * 3,
        },
        schema_overrides={"value": pl.Decimal(38, 6)},
    )
    results = {c.check_id: c for c in category_reconciliation(obs, catalog)}
    check = results[
        "reconciliation.category.censo_pessoas_quilombolas.c2661.territorios_quilombolas"
    ]
    assert check.status is CheckStatus.WARN
    assert check.details["divergent"][0]["residual"] == "10.000000"
