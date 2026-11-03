from pathlib import Path

import pytest
from pydantic import ValidationError

from odb_common.settings import config_file_path, load_settings


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in [k for k in __import__("os").environ if k.startswith("ODB_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("ODB_CONFIG_DIR", str(tmp_path))
    return tmp_path


def test_defaults_without_toml(config_dir: Path) -> None:
    settings = load_settings()
    assert settings.env == "dev"
    assert settings.lakehouse_root_uri == "file:///lakehouse"


def test_precedence_override_env_toml(config_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (config_dir / "test.toml").write_text('pg_database = "from_toml"\nduckdb_threads = 3\n')
    monkeypatch.setenv("ODB_ENV", "test")
    assert load_settings().pg_database == "from_toml"
    monkeypatch.setenv("ODB_PG_DATABASE", "from_env")
    assert load_settings().pg_database == "from_env"
    assert load_settings(pg_database="explicit").pg_database == "explicit"
    assert load_settings().duckdb_threads == 3


def test_config_file_path_follows_env(config_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODB_ENV", "test")
    assert config_file_path() == config_dir / "test.toml"


def test_disk_thresholds_validated(config_dir: Path) -> None:
    with pytest.raises(ValidationError):
        load_settings(disk_warn_percent=90, disk_block_percent=80)


def test_password_hidden_and_url_quoted(config_dir: Path) -> None:
    settings = load_settings(pg_user="odb_pipeline", pg_password="p@ss/w:rd", pg_host="db")
    assert "p@ss" not in repr(settings)
    url = settings.postgres_url()
    assert url.startswith("postgresql+psycopg://odb_pipeline:p%40ss%2Fw%3Ard@db:5432/odb")


def test_repository_toml_files_are_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_configs = Path(__file__).parents[3] / "configs" / "environments"
    for env in ("dev", "test"):
        monkeypatch.setenv("ODB_ENV", env)
        monkeypatch.setenv("ODB_CONFIG_DIR", str(repo_configs))
        assert load_settings().env == env
