"""Diagnóstico do ambiente (`odb doctor`)."""

from __future__ import annotations

import os
import platform
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from importlib.metadata import version
from pathlib import Path

import duckdb
from sqlalchemy import text

from odb_catalog import make_engine
from odb_catalog.migrate import current_revision, head_revision
from odb_common.settings import Settings
from odb_common.storage import LakehouseLayout, Layer, uri_to_local_path
from odb_lakehouse import DiskLevel, disk_status

PACKAGES = ("polars", "deltalake", "pyarrow", "duckdb", "sqlalchemy", "alembic", "psycopg")


class Status(StrEnum):
    """Resultado de uma verificação."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class Check:
    """Uma verificação do diagnóstico."""

    name: str
    status: Status
    detail: str


def _versions(_: Settings) -> list[Check]:
    detail = ", ".join(f"{p}={version(p)}" for p in PACKAGES)
    return [Check("versions", Status.OK, f"python={platform.python_version()}, {detail}")]


def _layers(settings: Settings) -> list[Check]:
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    checks: list[Check] = []
    for layer in Layer:
        path = Path(uri_to_local_path(layout.layer_uri(layer)))
        name = f"layer.{layer.value}"
        if not path.is_dir():
            checks.append(Check(name, Status.FAIL, f"diretório inexistente: {path}"))
            continue
        try:
            with tempfile.NamedTemporaryFile(dir=path, prefix=".odb-doctor-"):
                pass
            writable = "gravável"
        except OSError:
            writable = "somente leitura"
        status = disk_status(path, settings.disk_warn_percent, settings.disk_block_percent)
        level = {DiskLevel.OK: Status.OK, DiskLevel.WARN: Status.WARN}.get(
            status.level, Status.FAIL
        )
        free_gb = status.free_bytes / 1024**3
        checks.append(
            Check(
                name,
                level,
                f"{path} {writable}, disco {status.used_percent}% usado, {free_gb:.1f} GB livres",
            )
        )
    return checks


def _duckdb_delta(settings: Settings) -> list[Check]:
    config: dict[str, str | bool | int | float | list[str]] = {
        "autoinstall_known_extensions": False,
        "autoload_known_extensions": False,
    }
    if settings.duckdb_extension_directory:
        config["extension_directory"] = settings.duckdb_extension_directory
    try:
        with duckdb.connect(config=config) as con:
            con.execute("LOAD delta")
            row = con.execute(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name = 'delta'"
            ).fetchone()
    except duckdb.Error as exc:
        return [Check("duckdb.delta", Status.FAIL, f"extensão delta indisponível: {exc}")]
    return [Check("duckdb.delta", Status.OK, f"extensão delta {row[0] if row else '?'} carregada")]


def _postgres(settings: Settings) -> list[Check]:
    engine = make_engine(settings, pool_size=1)
    try:
        with engine.connect() as conn:
            server = conn.execute(text("SHOW server_version")).scalar()
        revision = current_revision(engine)
    except Exception as exc:
        return [Check("postgres", Status.FAIL, f"{type(exc).__name__}: {str(exc).splitlines()[0]}")]
    finally:
        engine.dispose()
    target = f"{settings.pg_user}@{settings.pg_host}:{settings.pg_port}/{settings.pg_database}"
    head = head_revision()
    migration = (
        Check("postgres.migrations", Status.OK, f"revisão {revision} (head)")
        if revision == head
        else Check("postgres.migrations", Status.FAIL, f"revisão {revision}, esperado {head}")
    )
    return [Check("postgres", Status.OK, f"{target} (PostgreSQL {server})"), migration]


def _threads(_: Settings) -> list[Check]:
    polars_threads = os.environ.get("POLARS_MAX_THREADS", "padrão")
    return [
        Check(
            "cpu", Status.OK, f"{os.cpu_count()} CPUs visíveis, POLARS_MAX_THREADS={polars_threads}"
        )
    ]


CHECKS: tuple[Callable[[Settings], list[Check]], ...] = (
    _versions,
    _threads,
    _layers,
    _duckdb_delta,
    _postgres,
)


def run_checks(settings: Settings) -> list[Check]:
    """Executa todas as verificações, sem interromper na primeira falha."""
    results: list[Check] = []
    for check in CHECKS:
        results.extend(check(settings))
    return results
