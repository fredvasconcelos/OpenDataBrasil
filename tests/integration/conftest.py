"""Fixtures de integração com PostgreSQL (banco odb_test).

Sem banco acessível, os testes são pulados. Com ``ODB_REQUIRE_INTEGRATION=1``
(container ``tests`` e CI), a indisponibilidade vira falha.
"""

import os
from collections.abc import Iterator

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from odb_catalog import make_engine
from odb_catalog.migrate import downgrade, upgrade
from odb_common.settings import Settings, load_settings

pytestmark = pytest.mark.integration


def _require() -> bool:
    return os.environ.get("ODB_REQUIRE_INTEGRATION") == "1"


@pytest.fixture(scope="session")
def pg_settings() -> Settings:
    settings = load_settings(pg_database=os.environ.get("ODB_PG_DATABASE", "odb_test"))
    if settings.pg_database != "odb_test":
        pytest.fail("testes de integração só rodam no banco odb_test")
    return settings


@pytest.fixture(scope="session")
def owner_engine(pg_settings: Settings) -> Iterator[Engine]:
    engine = make_engine(pg_settings)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        engine.dispose()
        if _require():
            pytest.fail(f"PostgreSQL indisponível: {exc}")
        pytest.skip(
            "PostgreSQL indisponível (defina ODB_PG_* ou suba `docker compose up postgres`)"
        )
    url = pg_settings.postgres_url()
    downgrade(url, "base")
    upgrade(url)
    yield engine
    engine.dispose()


@pytest.fixture
def engine(owner_engine: Engine) -> Engine:
    with owner_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE publication.release_event, publication.release_table, "
                "publication.release, operations.watermark, operations.bronze_artifact, "
                "operations.ingestion, operations.pipeline_run, catalog.dataset, catalog.source, "
                "catalog.license, catalog.institution"
            )
        )
    return owner_engine


def _role_engine(pg_settings: Settings, role: str, env_var: str) -> Iterator[Engine]:
    password = os.environ.get(env_var)
    if not password:
        if _require():
            pytest.fail(f"{env_var} não definida")
        pytest.skip(f"{env_var} não definida")
    eng = make_engine(
        pg_settings.model_copy(update={"pg_user": role, "pg_password": SecretStr(password)})
    )
    yield eng
    eng.dispose()


@pytest.fixture
def pipeline_engine(pg_settings: Settings, engine: Engine) -> Iterator[Engine]:
    yield from _role_engine(pg_settings, "odb_pipeline", "ODB_TEST_PIPELINE_PASSWORD")


@pytest.fixture
def reader_engine(pg_settings: Settings, engine: Engine) -> Iterator[Engine]:
    yield from _role_engine(pg_settings, "odb_reader", "ODB_TEST_READER_PASSWORD")
