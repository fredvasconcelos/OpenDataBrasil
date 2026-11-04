"""Bronze → Silver → Gold → release → consulta, pela CLI, com PostgreSQL real.

Fontes simuladas a partir de fixtures reais do SIDRA (níveis Brasil, Grande
Região e UF).
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from typer.testing import CliRunner

from odb_cli import ingest as ingest_cli
from odb_cli.main import app
from tests.gold_support import REPO_INDICATORS
from tests.ingestion_support import TEST_SOURCES, FakeSources

pytestmark = pytest.mark.integration


@pytest.fixture
def lake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: Engine) -> Path:
    root = tmp_path / "lake"
    for layer in ("bronze", "silver", "gold", "tmp"):
        (root / layer).mkdir(parents=True)
    monkeypatch.setenv("ODB_LAKEHOUSE_ROOT_URI", root.as_uri())
    monkeypatch.setenv("ODB_SOURCES_CONFIG_DIR", str(TEST_SOURCES))
    monkeypatch.setenv("ODB_INDICATORS_CONFIG_DIR", str(REPO_INDICATORS))
    monkeypatch.setenv("ODB_DUCKDB_TEMP_DIRECTORY", str(tmp_path / "duck"))
    monkeypatch.setenv("ODB_DUCKDB_MEMORY_LIMIT", "512MB")
    monkeypatch.setenv("ODB_DUCKDB_THREADS", "2")
    monkeypatch.setenv("ODB_PG_DATABASE", "odb_test")
    monkeypatch.setattr(ingest_cli, "HTTP_TRANSPORT", FakeSources().transport())
    return root


def _q(engine: Engine, sql: str) -> list[tuple[object, ...]]:
    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql)).all()]


def _query(runner: CliRunner, *args: str) -> Any:
    result = runner.invoke(app, ["query", *args, "--format", "json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _values(payload: Any) -> dict[tuple[str, str], str]:
    rows = payload["rows"]
    assert isinstance(rows, list)
    return {(r["geography_key"], r["breakdown_key"]): format(float(r["value"]), "g") for r in rows}


def test_gold_publish_query_and_preserve_on_failure(  # noqa: PLR0915 - cenário ponta a ponta
    lake: Path, engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["ingest", "run", "--all"]).exit_code == 0
    assert runner.invoke(app, ["silver", "build", "--all"]).exit_code == 0

    # Sem release ativo, a consulta é recusada.
    assert runner.invoke(app, ["query", "-i", "censo_pessoas_quilombolas"]).exit_code == 1

    built = runner.invoke(app, ["gold", "build", "--activate"])
    assert built.exit_code == 0, built.output
    first = json.loads(built.stdout)
    assert first["status"] == "succeeded"
    assert first["release"]["status"] == "active"
    release_id = first["release"]["release_id"]
    assert len(first["tables"]) == 14
    assert "fact_indigenous_population" in first["tables"]

    # Catálogo de indicadores e vínculo construção → release no PostgreSQL.
    assert _q(engine, "SELECT count(*) FROM catalog.indicator")[0][0] == 11
    assert _q(engine, "SELECT release_id::text FROM operations.gold_build")[0][0] == release_id
    statuses = {
        str(k): v
        for k, v in _q(engine, "SELECT status, count(*) FROM quality.gold_check_result GROUP BY 1")
    }
    assert "fail" not in statuses

    # Pessoas quilombolas por UF (valores oficiais publicados).
    quilombolas = _query(runner, "-i", "censo_pessoas_quilombolas", "--level", "uf", "-p", "2022")
    assert quilombolas["provenance"]["release_id"] == release_id
    values = _values(quilombolas)
    assert len(values) == 27
    assert values[("uf:29", "c2661:32776")] == "397502"  # Bahia (fixture t9578, 2ª apuração)

    # Cor ou raça, por UF do Nordeste, 2010 e 2022, todas as categorias.
    race = _query(
        runner,
        "-i",
        "censo_populacao_cor_raca",
        "--level",
        "uf",
        "--within",
        "regiao:2",
        "--by",
        "c86",
        "-p",
        "2010",
        "-p",
        "2022",
    )
    rows = race["rows"]
    assert isinstance(rows, list)
    assert len(rows) == 9 * 6 * 2
    assert {r["geography_key"] for r in rows} == {f"uf:{c}" for c in range(21, 30)}

    # Só a categoria Indígena, no Brasil: a desagregação filtra categorias.
    indigenous_race = _values(
        _query(runner, "-i", "censo_populacao_cor_raca", "--level", "brasil", "--by", "c86=2780")
    )
    assert set(indigenous_race) == {("brasil:1", "c86:2780")}

    # Pessoas indígenas por quesito de declaração (Total de localização).
    by_question = _values(
        _query(runner, "-i", "censo_pessoas_indigenas", "--level", "brasil", "--by", "c1714")
    )
    assert by_question[("brasil:1", "c1714:60024|c2661:32776")] == "1.69484e+06"
    assert by_question[("brasil:1", "c1714:60026|c2661:32776")] == "467194"

    # Soma das UFs até a Grande Região: derivada, igual ao total oficial (contagem exata).
    summed = _query(
        runner, "-i", "censo_pessoas_quilombolas", "--level", "uf", "--sum-to", "regiao"
    )
    assert summed["provenance"]["derived"] is True
    official = _values(
        _query(runner, "-i", "censo_pessoas_quilombolas", "--level", "regiao", "--by", "c2661")
    )
    summed_values = _values(summed)
    assert summed_values[("regiao:2", "c2661:32776")] == official[("regiao:2", "c2661:32776")]
    assert any("derivado" in w for w in summed["warnings"])
    assert {r["children_pending_installation"] for r in summed["rows"]} == {0}

    # Regras semânticas.
    rejected = runner.invoke(
        app, ["query", "-i", "censo_percentual_indigenas", "--level", "uf", "--sum-to", "brasil"]
    )
    assert rejected.exit_code == 2
    assert "não aditivos" in rejected.output
    mixed = runner.invoke(
        app, ["query", "-i", "censo_pessoas_indigenas", "-i", "censo_populacao_cor_raca"]
    )
    assert mixed.exit_code == 2
    assert "definições diferentes de população indígena" in mixed.output
    no_level = runner.invoke(app, ["query", "-i", "populacao_estimada", "--level", "municipio"])
    assert no_level.exit_code == 2
    assert "níveis disponíveis" in no_level.output

    # Catálogo navegável.
    tree = runner.invoke(app, ["indicators", "tree"])
    assert tree.exit_code == 0
    assert "        Se considera indígena  [c1714=60026]" in tree.stdout
    listing = runner.invoke(app, ["indicators", "list", "--json"])
    assert len(json.loads(listing.stdout)["indicators"]) == 11
    report = runner.invoke(app, ["quality", "gold"])
    assert report.exit_code == 0
    assert "reconciliation.category.censo_populacao_cor_raca.c86.cor_ou_raca" in report.stdout

    # Exportação do release ativo para análise local.
    exports = tmp_path / "exports"
    exports.mkdir()
    exported = runner.invoke(app, ["gold", "export", "--out", str(exports)])
    assert exported.exit_code == 0, exported.output
    export_info = json.loads(exported.stdout)
    assert export_info["release_id"] == release_id
    assert export_info["tables"]["indicator_observation"] == 2706
    manifest = json.loads((Path(export_info["path"]) / "manifest.json").read_text())
    assert manifest["provenance"]["license_review_status"] == "requires_review"
    missing_dir = runner.invoke(app, ["gold", "export", "--out", str(tmp_path / "nao-existe")])
    assert missing_dir.exit_code == 1

    # Reexecução sem mudança: skipped, sem release novo.
    again = json.loads(runner.invoke(app, ["gold", "build", "--activate"]).stdout)
    assert again["status"] == "skipped"
    assert again["release"]["release_id"] == release_id
    assert _q(engine, "SELECT count(*) FROM publication.release")[0][0] == 1

    # Falha: catálogo com unidade divergente da publicada. Nada é escrito nem publicado.
    broken = tmp_path / "indicators"
    broken.mkdir()
    shutil.copy(REPO_INDICATORS / "demografia.toml", broken / "demografia.toml")
    path = broken / "demografia.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'unit = "Quilômetros quadrados"', 'unit = "Hectares"'
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ODB_INDICATORS_CONFIG_DIR", str(broken))
    failed = runner.invoke(app, ["gold", "build", "--activate"])
    assert failed.exit_code == 1
    failure = json.loads(failed.stdout)
    assert failure["status"] == "failed"
    assert "semantics.unit" in failure["error"]
    assert failure["active_release"] == release_id
    assert _q(engine, "SELECT count(*) FROM publication.release")[0][0] == 1
    assert _q(
        engine,
        "SELECT status FROM operations.pipeline_run WHERE command = 'gold.build' "
        "ORDER BY started_at DESC LIMIT 1",
    ) == [("failed",)]

    # A consulta continua servindo o release anterior.
    monkeypatch.setenv("ODB_INDICATORS_CONFIG_DIR", str(REPO_INDICATORS))
    still = _query(runner, "-i", "censo_pessoas_quilombolas", "--level", "brasil")
    assert still["provenance"]["release_id"] == release_id

    # Reconstrução forçada gera release validado (não ativo) e ativação manual.
    rebuilt = json.loads(runner.invoke(app, ["gold", "build", "--force"]).stdout)
    assert rebuilt["status"] == "succeeded"
    assert rebuilt["release"]["status"] == "validated"
    activated = runner.invoke(app, ["release", "activate", rebuilt["release"]["release_id"]])
    assert activated.exit_code == 0, activated.output
    releases = json.loads(runner.invoke(app, ["release", "list"]).stdout)
    assert [r["status"] for r in releases] == ["active", "superseded"]
