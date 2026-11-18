"""Comandos `odb silver` e `odb quality`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from odb_catalog import PostgresAdvisoryLock, make_engine, tracked_run
from odb_catalog.ingestion import PostgresIngestionRegistry
from odb_catalog.silver import PostgresSilverRegistry
from odb_common.logging import configure_logging
from odb_common.settings import Settings, load_settings
from odb_common.storage import LakehouseLayout
from odb_ingestion import load_sources
from odb_lakehouse import DeltaWriter
from odb_processing.silver import SilverBuilder, results_to_json

silver_app = typer.Typer(no_args_is_help=True, help="Camada Silver (Delta Lake).")
quality_app = typer.Typer(no_args_is_help=True, help="Resultados de qualidade de dados.")


class SilverFailedError(RuntimeError):
    """Um ou mais datasets falharam."""


def _settings() -> Settings:
    settings = load_settings()
    configure_logging(settings.log_level)
    return settings


def _echo_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


@silver_app.command("build")
def silver_build(
    dataset_ids: Annotated[list[str] | None, typer.Argument(help="Datasets a transformar.")] = None,
    all_datasets: Annotated[
        bool, typer.Option("--all", help="Todos com transformação Silver.")
    ] = False,
    force: Annotated[bool, typer.Option(help="Reconstrói mesmo sem mudança na Bronze.")] = False,
) -> None:
    """Constrói a Silver a partir dos artefatos Bronze vigentes."""
    settings = _settings()
    catalog = load_sources(settings.sources_config_dir)
    targets = (
        [d.id for d in catalog.datasets.values() if d.enabled and d.silver] if all_datasets else []
    )
    targets += [d for d in dataset_ids or [] if d not in targets]
    if not targets:
        typer.echo("informe os datasets ou use --all", err=True)
        raise typer.Exit(code=2)
    for dataset_id in targets:
        catalog.dataset(dataset_id)
    engine = make_engine(settings, pool_size=3)
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    writer = DeltaWriter(
        layout,
        PostgresAdvisoryLock(engine),
        disk_warn_percent=settings.disk_warn_percent,
        disk_block_percent=settings.disk_block_percent,
    )
    builder = SilverBuilder(
        catalog,
        layout,
        writer,
        PostgresSilverRegistry(engine),
        code_version=settings.code_version,
        config_dir=Path(settings.sources_config_dir),
    )
    # Datasets precisam existir no catálogo (FK de transformation_run), mesmo sem ingestão.
    PostgresIngestionRegistry(engine).sync_catalog(catalog)
    summary: list[dict[str, Any]] = []
    try:
        with tracked_run(
            engine, "silver.build", settings.code_version, {"datasets": targets, "force": force}
        ) as run_id:
            for run in builder.build_many(targets, pipeline_run_id=run_id, force=force):
                summary.append(
                    {
                        "dataset_id": run.dataset_id,
                        "status": run.status,
                        "target_uri": run.target_uri,
                        "delta_version": run.delta_version,
                        "rows": run.rows,
                        "checks": run.stats()["checks"],
                        "warnings": [c.check_id for c in run.checks if c.status.value == "warn"],
                        "error": run.error,
                    }
                )
            failed = [s["dataset_id"] for s in summary if s["status"] == "failed"]
            if failed:
                msg = f"datasets com falha: {failed}"
                raise SilverFailedError(msg)
    except SilverFailedError:
        _echo_json(summary)
        raise typer.Exit(code=1) from None
    finally:
        engine.dispose()
    _echo_json(summary)


@quality_app.command("report")
def quality_report(
    dataset_id: str,
    as_json: Annotated[bool, typer.Option("--json", help="Saída em JSON com detalhes.")] = False,
) -> None:
    """Resultados de qualidade da última execução Silver do dataset."""
    settings = _settings()
    engine = make_engine(settings, pool_size=1)
    try:
        run, checks = PostgresSilverRegistry(engine).latest_report(dataset_id)
    finally:
        engine.dispose()
    if run is None:
        typer.echo(f"nenhum resultado de qualidade para {dataset_id}", err=True)
        raise typer.Exit(code=1)
    if as_json:
        _echo_json({"run": run, "checks": checks})
        return
    typer.echo(
        f"{dataset_id}: execução {run['run_id']} ({run['status']}, Delta v{run['delta_version']}, "
        f"{run['contract']} {run['contract_version']}) em {run['started_at']:%Y-%m-%d %H:%M:%S}"
    )
    for c in checks:
        typer.echo(f"  [{c['status'].upper():4}] {c['check_id']:34} {c['message']}")


__all__ = ["quality_app", "results_to_json", "silver_app"]
