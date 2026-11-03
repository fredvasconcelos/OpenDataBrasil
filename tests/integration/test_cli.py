import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from typer.testing import CliRunner

from odb_cli.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def lake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: Engine) -> Path:
    root = tmp_path / "lake"
    for layer in ("bronze", "silver", "gold", "tmp"):
        (root / layer).mkdir(parents=True)
    monkeypatch.setenv("ODB_LAKEHOUSE_ROOT_URI", root.as_uri())
    monkeypatch.setenv("ODB_DUCKDB_TEMP_DIRECTORY", str(root / "tmp" / "duckdb"))
    monkeypatch.setenv("ODB_PG_DATABASE", "odb_test")
    return root


def test_db_commands(lake: Path) -> None:
    runner = CliRunner()
    up = runner.invoke(app, ["db", "upgrade"])
    assert up.exit_code == 0, up.output
    assert "revisão 0002" in up.output
    cur = runner.invoke(app, ["db", "current"])
    assert "atual=0002 head=0002" in cur.output


def test_doctor_all_green(lake: Path) -> None:
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "[FAIL]" not in result.output
    assert "postgres.migrations" in result.output


def test_smoke_lakehouse(lake: Path, engine: Engine) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["smoke", "lakehouse"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["versions"] == [0, 1, 2]
    assert (report["v0_rows"], report["latest_rows"]) == (3, 5)
    assert not list((lake / "tmp" / "smoke").iterdir())  # removida sem --keep
    with engine.connect() as conn:
        status = conn.execute(
            text("SELECT status FROM operations.pipeline_run WHERE run_id = :id"),
            {"id": report["run_id"]},
        ).scalar()
    assert status == "succeeded"

    kept = runner.invoke(app, ["smoke", "lakehouse", "--keep"])
    assert kept.exit_code == 0, kept.output
    assert len(list((lake / "tmp" / "smoke").iterdir())) == 1
