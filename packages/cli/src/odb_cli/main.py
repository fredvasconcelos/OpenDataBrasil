"""Ponto de entrada da CLI `odb`."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Annotated

import typer

from odb_catalog import make_engine
from odb_catalog.migrate import current_revision, head_revision, upgrade
from odb_cli.doctor import Status, run_checks
from odb_cli.ingest import ingest_app, sources_app
from odb_cli.smoke import run_lakehouse_smoke
from odb_common.logging import configure_logging
from odb_common.settings import Settings, load_settings

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Operação da plataforma OpenDataBrasil."
)
db_app = typer.Typer(no_args_is_help=True, help="Banco operacional (PostgreSQL).")
smoke_app = typer.Typer(no_args_is_help=True, help="Smoke tests do ambiente.")
app.add_typer(db_app, name="db")
app.add_typer(smoke_app, name="smoke")
app.add_typer(sources_app, name="sources")
app.add_typer(ingest_app, name="ingest")

logger = logging.getLogger("odb.cli")


def _settings() -> Settings:
    settings = load_settings()
    configure_logging(settings.log_level)
    return settings


@app.command()
def doctor(
    as_json: Annotated[bool, typer.Option("--json", help="Saída em JSON.")] = False,
) -> None:
    """Verifica versões, camadas, disco, extensão Delta do DuckDB e PostgreSQL."""
    settings = _settings()
    checks = run_checks(settings)
    if as_json:
        typer.echo(json.dumps([asdict(c) for c in checks], ensure_ascii=False, indent=2))
    else:
        for c in checks:
            typer.echo(f"[{c.status.value.upper():4}] {c.name:22} {c.detail}")
    if any(c.status is Status.FAIL for c in checks):
        raise typer.Exit(code=1)


@db_app.command("upgrade")
def db_upgrade(revision: str = "head") -> None:
    """Aplica migrações Alembic (executar com o role odb_owner)."""
    settings = _settings()
    upgrade(settings.postgres_url(), revision)
    engine = make_engine(settings, pool_size=1)
    try:
        typer.echo(f"banco {settings.pg_database} na revisão {current_revision(engine)}")
    finally:
        engine.dispose()


@db_app.command("current")
def db_current() -> None:
    """Mostra a revisão aplicada e a revisão head disponível."""
    settings = _settings()
    engine = make_engine(settings, pool_size=1)
    try:
        typer.echo(f"atual={current_revision(engine)} head={head_revision()}")
    finally:
        engine.dispose()


@smoke_app.command("lakehouse")
def smoke_lakehouse(
    keep: Annotated[bool, typer.Option(help="Mantém a tabela de smoke em tmp/.")] = False,
) -> None:
    """Escreve v0 a v2 em tmp/, lê a v0 por Polars e DuckDB e compara."""
    settings = _settings()
    report = run_lakehouse_smoke(settings, keep=keep)
    typer.echo(json.dumps({"status": "ok", **asdict(report)}, ensure_ascii=False, indent=2))
