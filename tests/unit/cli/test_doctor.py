import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from odb_cli.doctor import Status, _duckdb_delta, run_checks
from odb_cli.main import app
from odb_common.settings import Settings
from tests.support import EXTENSION_DIR_ENV


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in [k for k in os.environ if k.startswith("ODB_") and k != EXTENSION_DIR_ENV]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("ODB_CONFIG_DIR", str(tmp_path / "no-config"))
    monkeypatch.setenv("ODB_LAKEHOUSE_ROOT_URI", (tmp_path / "lake").as_uri())
    monkeypatch.setenv("ODB_PG_HOST", "127.0.0.1")
    monkeypatch.setenv("ODB_PG_PORT", "1")  # porta fechada: falha rápida
    monkeypatch.setenv("ODB_PG_CONNECT_TIMEOUT_S", "1")
    return tmp_path / "lake"


def test_doctor_reports_missing_layers_and_postgres(isolated_env: Path) -> None:
    checks = {c.name: c for c in run_checks(Settings())}
    assert checks["versions"].status is Status.OK
    assert "polars=1.44.2" in checks["versions"].detail
    assert checks["layer.gold"].status is Status.FAIL
    assert checks["duckdb.delta"].status is Status.OK
    assert checks["postgres"].status is Status.FAIL


def test_doctor_layers_ok_when_present(isolated_env: Path) -> None:
    for layer in ("bronze", "silver", "gold", "tmp"):
        (isolated_env / layer).mkdir(parents=True)
    (isolated_env / "gold").chmod(0o555)
    try:
        checks = {c.name: c for c in run_checks(Settings())}
    finally:
        (isolated_env / "gold").chmod(0o755)
    assert checks["layer.silver"].status in (Status.OK, Status.WARN)
    assert "gravável" in checks["layer.silver"].detail
    assert "somente leitura" in checks["layer.gold"].detail


def test_doctor_cli_exit_code_and_json(isolated_env: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "[FAIL] postgres" in result.output
    as_json = runner.invoke(app, ["doctor", "--json"])
    assert as_json.exit_code == 1
    assert '"name": "duckdb.delta"' in as_json.output


def test_duckdb_extension_missing_is_reported(isolated_env: Path, tmp_path: Path) -> None:
    checks = _duckdb_delta(Settings(duckdb_extension_directory=str(tmp_path / "empty")))
    assert checks[0].status is Status.FAIL
