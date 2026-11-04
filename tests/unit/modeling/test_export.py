import json
from pathlib import Path

import duckdb
import polars as pl
import pytest

from odb_modeling.export import ExportError, ReleaseToExport, export_release, read_observations
from tests.gold_support import GoldEnv


@pytest.fixture
def release(tmp_path: Path) -> ReleaseToExport:
    env = GoldEnv(tmp_path)
    env.prepare()
    build = env.gold.build()
    assert build.status == "succeeded"
    return ReleaseToExport("r-1", "demografia", "active", None, build.tables)


def test_export_parquet_duckdb_and_manifest(release: ReleaseToExport, tmp_path: Path) -> None:
    out = tmp_path / "exports"
    result = export_release(release, out, provenance={"license": "x", "sources": ["IBGE"]})
    assert result.status == "created"
    assert result.path == out / "demografia" / "r-1"
    manifest = json.loads((result.path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["official"] is False
    assert manifest["tables"]["indicator_observation"]["rows"] == 10032
    assert manifest["tables"]["dim_geography"]["delta_version"] == 0
    assert "NÃO É FONTE OFICIAL" in (result.path / "LEIAME.txt").read_text(encoding="utf-8")
    assert json.loads((out / "demografia" / "latest.json").read_text())["release_id"] == "r-1"
    assert not list((out / "demografia").glob(".tmp-*"))

    obs = pl.read_parquet(result.path / "parquet" / "indicator_observation.parquet")
    assert obs.schema["value"] == pl.Decimal(38, 6)

    with duckdb.connect(str(result.path / "gold.duckdb"), read_only=True) as con:
        row = con.execute(
            "SELECT territory_name, value_double, breakdown_label FROM observacoes "
            "WHERE indicator_id = 'censo_pessoas_quilombolas' AND geography_key = 'uf:29' "
            "AND non_total_count = 0"
        ).fetchall()
        assert row == [("Bahia", 397502.0, "Total")]
        assert con.execute("SELECT count(*) FROM arvore_indicadores").fetchone() == (237,)

    lazy = read_observations(result.path)
    brasil = lazy.filter(
        (pl.col("indicator_id") == "censo_pessoas_indigenas")
        & (pl.col("geography_key") == "brasil:1")
        & (pl.col("non_total_count") == 0)
    ).collect()
    assert brasil["value_double"].to_list() == [1694836.0]

    again = export_release(release, out)
    assert again.status == "existing"
    forced = export_release(release, out, force=True)
    assert forced.status == "created"


def test_export_refuses_unpublished_and_foreign_dirs(
    release: ReleaseToExport, tmp_path: Path
) -> None:
    draft = ReleaseToExport("r-2", "demografia", "validated", None, release.tables)
    with pytest.raises(ExportError, match="publicados"):
        export_release(draft, tmp_path)
    with pytest.raises(ExportError, match="sem tabelas"):
        export_release(ReleaseToExport("r-3", "demografia", "active", None, {}), tmp_path)
    foreign = tmp_path / "demografia" / "r-1"
    foreign.mkdir(parents=True)
    (foreign / "meu-arquivo.txt").write_text("não apagar")
    with pytest.raises(ExportError, match="nada foi apagado"):
        export_release(release, tmp_path, force=True)
    assert (foreign / "meu-arquivo.txt").exists()
