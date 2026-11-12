import json
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
import shapely
from deltalake import DeltaTable

from odb_lakehouse import DeltaReader
from odb_modeling import model
from odb_modeling.builder import GoldBuilder
from odb_modeling.geography import GeographyError, build_ancestor_bridge, build_dim_geography
from odb_modeling.quality import category_reconciliation, consistency_checks
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
    assert obs.height == 17763
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
    consistency = {k: c for k, c in checks.items() if k.startswith("consistency.")}
    assert len(consistency) == 6
    assert {c.status for c in consistency.values()} == {CheckStatus.PASS}, {
        k: c.message for k, c in consistency.items()
    }
    # 9606 = 9605: 6 categorias de cor ou raça x 33 territórios x 2 anos.
    assert (
        consistency["consistency.censo_populacao_cor_raca_sexo.censo_populacao_cor_raca"].observed
        == 396
    )

    sex = _read(build.tables["fact_population_by_race_sex"]).filter(
        (pl.col("geography_key") == "brasil:1") & (pl.col("race_category_key") == "c86:95251")
    )
    by_sex = {
        (r["period"], r["sex_category_key"]): r["population"] for r in sex.iter_rows(named=True)
    }
    assert by_sex[("2022", "c2:4")] == Decimal("98532431")
    assert by_sex[("2022", "c2:5")] == Decimal("104548325")
    assert by_sex[("2010", "c2:6794")] == Decimal("190755799")
    quilombola = _read(build.tables["fact_quilombola_by_sex"]).filter(
        (pl.col("geography_key") == "brasil:1") & (pl.col("location_category_key") == "c2661:32776")
    )
    assert sorted(quilombola["quilombola_persons"].to_list()) == [
        Decimal("664833"),
        Decimal("665353"),
        Decimal("1330186"),
    ]
    territory = (
        _read(build.tables["fact_quilombola_territory_by_sex"])
        .filter((pl.col("geography_key") == "brasil:1") & (pl.col("sex_category_key") == "c2:4"))
        .row(0, named=True)
    )
    assert (territory["residents"], territory["quilombola_persons"]) == (
        Decimal("104555"),
        Decimal("86284"),
    )


def test_geometry_levels_and_lagoons(env: GoldEnv) -> None:
    build = env.gold.build()
    assert build.status == "succeeded", build.error
    checks = {c.check_id: c for c in build.checks}
    geometry = _read(build.tables["dim_geometry"])
    assert dict(geometry.group_by("level_id").len().iter_rows()) == {
        "municipio": 3,  # as lagoas (4300001, 4300002) não são municípios
        "uf": 27,
        "regiao": 5,
        "brasil": 1,
    }
    nordeste = geometry.filter(pl.col("geography_key") == "regiao:2").row(0, named=True)
    assert nordeste["derivation"] == "union:uf"
    assert nordeste["crs"] == "EPSG:4674"
    assert json.loads(nordeste["geometry_geojson"])["type"] in {"Polygon", "MultiPolygon"}
    # RFC 7946: anel externo anti-horário em todas as geometrias.
    for text in geometry["geometry_geojson"].to_list():
        geom = shapely.from_geojson(text)
        polygons = getattr(geom, "geoms", [geom])
        assert all(p.exterior.is_ccw for p in polygons)
    coverage = checks["geometry.coverage"]
    assert coverage.status is CheckStatus.WARN  # 5.568 municípios sem polígono na malha sintética
    assert coverage.details["dropped_polygons"]["municipio"] == [
        {"code": "4300001", "name": "Lagoa Mirim"},
        {"code": "4300002", "name": "Lagoa dos Patos"},
    ]
    assert checks["geometry.valid"].status is CheckStatus.PASS
    assert checks["fk.geometry.geography"].status is CheckStatus.PASS


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
    # Com a gravação por lote (KI-007, etapa 2), lotes podem ter sido gravados antes da
    # verificação final; o build falho não registra tabelas e não gera release.
    assert not build.tables


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


def test_municipal_names_keep_what_the_lookups_need() -> None:
    """O recorte enxuto (KI-007) dá o mesmo resultado que as observações inteiras."""
    rows = _silver_rows([("2299901", "Aroeiras do Itaim - PI"), ("5099902", "Figueirão - MS")])
    observations = pl.concat(
        [
            rows.with_columns(pl.lit("93").alias("variable_id")),
            rows.with_columns(pl.lit("1000").alias("variable_id")),  # mesma linha, outra variável
            rows.with_columns(
                pl.lit("93").alias("variable_id"),
                pl.lit("3").alias("territorial_level"),
                pl.lit("22").alias("territory_id"),
            ),
        ]
    )
    names = model.municipal_names(observations.lazy())
    assert names.columns == list(model.MUNICIPAL_NAME_COLUMNS)
    assert names.height == 2  # só municípios, sem repetição por variável
    assert model.uf_abbreviations(names) == model.uf_abbreviations(observations)


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
    # Terras indígenas: Yanomami (8656) está em AM e RR.
    assert counts["terra_indigena"] == 573
    assert counts["terra_indigena_uf"] == 602
    assert counts["coordenacao_regional_funai"] == 39
    yanomami = bridge.filter(pl.col("ancestor_key") == "terra_indigena:8656")["geography_key"]
    assert sorted(yanomami.to_list()) == [
        "terra_indigena:8656",
        "terra_indigena_uf:1308656",
        "terra_indigena_uf:1408656",
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


def test_consistency_compares_common_categories_with_others_at_total() -> None:
    catalog = load_catalog(REPO_INDICATORS / "demografia.toml")
    rows = [
        # 8176: sexo no Total entra na comparação; Homens fica de fora.
        ("censo_pessoas_quilombolas_sexo", "c287:100362|c2661:32776|c2:6794", "100", "valid"),
        ("censo_pessoas_quilombolas_sexo", "c287:100362|c2661:60027|c2:6794", "41", "valid"),
        ("censo_pessoas_quilombolas_sexo", "c287:100362|c2661:60028|c2:6794", "59", "valid"),
        ("censo_pessoas_quilombolas_sexo", "c287:100362|c2661:32776|c2:4", "999", "valid"),
        # 9578: 60027 diverge; 60028 é suprimido e não é comparado.
        ("censo_pessoas_quilombolas", "c2661:32776", "100", "valid"),
        ("censo_pessoas_quilombolas", "c2661:60027", "40", "valid"),
        ("censo_pessoas_quilombolas", "c2661:60028", None, "suppressed"),
    ]
    obs = pl.DataFrame(
        {
            "indicator_id": [r[0] for r in rows],
            "geography_key": ["uf:29"] * len(rows),
            "period": ["2022"] * len(rows),
            "breakdown_key": [r[1] for r in rows],
            "value": [None if r[2] is None else Decimal(r[2]) for r in rows],
            "value_status": [r[3] for r in rows],
        },
        schema_overrides={"value": pl.Decimal(38, 6)},
    )
    results = {c.check_id: c for c in consistency_checks(obs, catalog)}
    check = results["consistency.censo_pessoas_quilombolas_sexo.censo_pessoas_quilombolas"]
    assert check.status is CheckStatus.WARN
    assert check.details["compared"] == 2
    assert check.details["not_comparable"] == 1
    assert check.details["divergent"][0]["context"] == "c2661:60027"
    # Pares sem observações avisam em vez de passar em silêncio.
    empty = results["consistency.censo_populacao_cor_raca_sexo.censo_populacao_cor_raca"]
    assert empty.status is CheckStatus.WARN
    assert empty.observed == 0


def test_chunks_split_large_datasets_by_table_and_year(monkeypatch: pytest.MonkeyPatch) -> None:
    """KI-007: dataset grande vira sub-lotes de tabela e ano; pequeno fica num só."""
    from odb_modeling import builder as b  # noqa: PLC0415

    monkeypatch.setattr(b, "CHUNK_ROWS", 100)
    sizes = {
        ("T-2015", "2015"): 80,
        ("T-2016", "2016"): 80,
        ("T-2017", "2017"): 10,
        ("X", "2022"): 5,
    }
    assert b._chunks(("T-2015", "T-2016", "T-2017"), sizes) == [
        [("T-2015", "2015")],
        [("T-2016", "2016"), ("T-2017", "2017")],
    ]
    assert b._chunks(("X",), sizes) == [[("X", "2022")]]
    # Sem linhas na Silver: um lote com a tabela inteira (fatos vazios ainda são gravados).
    assert b._chunks(("Y",), sizes) == [[("Y", None)]]


def test_reconciliation_parts_are_merged() -> None:
    from odb_modeling.quality import merge_reconciliation  # noqa: PLC0415
    from odb_processing.quality import CheckResult, CheckStatus  # noqa: PLC0415

    cid = "reconciliation.category.x.c2.sexo"
    ok = CheckResult(
        cid,
        CheckStatus.PASS,
        "3 totais conferem (categorias = Total)",
        observed=3,
        details={"exhaustive": True, "compared": 3, "skipped": 0},
    )
    bad = CheckResult(
        cid,
        CheckStatus.WARN,
        "1 de 2 totais divergem",
        observed=1,
        expected=0,
        details={"exhaustive": True, "compared": 2, "skipped": 1, "divergent": [{"a": "1"}]},
    )
    [merged] = merge_reconciliation([ok, bad])
    assert merged.status is CheckStatus.WARN
    assert (merged.observed, merged.details["compared"], merged.details["skipped"]) == (1, 5, 1)
    [both_ok] = merge_reconciliation([ok, ok])
    assert (both_ok.status, both_ok.message) == (
        CheckStatus.PASS,
        "6 totais conferem (categorias = Total)",
    )
