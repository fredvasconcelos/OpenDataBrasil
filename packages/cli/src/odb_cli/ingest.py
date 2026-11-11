"""Comandos `odb sources` e `odb ingest`."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
from sqlalchemy import Engine

from odb_catalog import make_engine, tracked_run
from odb_catalog.ingestion import PostgresIngestionRegistry
from odb_common.logging import configure_logging
from odb_common.settings import Settings, load_settings
from odb_common.storage import LakehouseLayout
from odb_ingestion import (
    BaseConnector,
    BronzeStore,
    HttpClient,
    IngestionRunner,
    SourceCatalog,
    build_connectors,
    load_sources,
)
from odb_lakehouse.disk import ensure_capacity

sources_app = typer.Typer(no_args_is_help=True, help="Fontes de dados configuradas.")
ingest_app = typer.Typer(no_args_is_help=True, help="Ingestão de dados oficiais para a Bronze.")

# Substituível em testes para simular as fontes sem acesso à rede.
HTTP_TRANSPORT: httpx.BaseTransport | None = None


class IngestionFailedError(RuntimeError):
    """Um ou mais datasets falharam."""


@dataclass
class _Runtime:
    settings: Settings
    catalog: SourceCatalog
    connectors: dict[str, BaseConnector]
    engine: Engine
    runner: IngestionRunner


def _settings() -> Settings:
    settings = load_settings()
    configure_logging(settings.log_level)
    return settings


def _http(connector: BaseConnector) -> HttpClient:
    return HttpClient(connector.source.http, transport=HTTP_TRANSPORT)


def _runtime(settings: Settings) -> _Runtime:
    catalog = load_sources(settings.sources_config_dir)
    connectors = build_connectors(catalog)
    engine = make_engine(settings, pool_size=2)
    bronze = BronzeStore(LakehouseLayout(settings.lakehouse_root_uri))
    root: Path = bronze.bronze_root

    def capacity() -> None:
        ensure_capacity(root, settings.disk_warn_percent, settings.disk_block_percent)

    runner = IngestionRunner(
        catalog,
        connectors,
        bronze,
        PostgresIngestionRegistry(engine),
        _http,
        capacity_check=capacity,
    )
    return _Runtime(settings, catalog, connectors, engine, runner)


def _echo_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


@sources_app.command("list")
def sources_list() -> None:
    """Lista instituições, fontes e datasets configurados."""
    catalog = load_sources(_settings().sources_config_dir)
    for ds in catalog.datasets.values():
        source = catalog.sources[ds.source]
        flag = "" if ds.enabled else " [desabilitado]"
        typer.echo(f"{ds.id:20} {source.connector:10} {ds.official_id:10} {ds.title}{flag}")


@sources_app.command("health")
def sources_health() -> None:
    """Verifica a disponibilidade de cada fonte (sai com 1 se alguma falhar)."""
    catalog = load_sources(_settings().sources_config_dir)
    failed = False
    for source_id, connector in build_connectors(catalog).items():
        with _http(connector) as http:
            status = connector.healthcheck(http)
        failed |= not status.ok
        label = "OK" if status.ok else "FAIL"
        latency = f" ({status.latency_ms} ms)" if status.latency_ms is not None else ""
        typer.echo(f"[{label:4}] {source_id:14} {status.detail}{latency}")
    if failed:
        raise typer.Exit(code=1)


@ingest_app.command("plan")
def ingest_plan(
    dataset_id: str,
    full: Annotated[bool, typer.Option(help="Ignora o watermark.")] = False,
) -> None:
    """Mostra as requisições que seriam feitas (consulta apenas a descoberta da fonte)."""
    rt = _runtime(_settings())
    try:
        rt.runner.sync_catalog()
        _echo_json(rt.runner.plan(dataset_id, full=full).to_json())
    finally:
        rt.engine.dispose()


@ingest_app.command("run")
def ingest_run(  # noqa: PLR0917 - opções da linha de comando (Typer)
    dataset_ids: Annotated[list[str] | None, typer.Argument(help="Datasets a ingerir.")] = None,
    all_datasets: Annotated[bool, typer.Option("--all", help="Todos os habilitados.")] = False,
    full: Annotated[bool, typer.Option(help="Baixa todas as partições.")] = False,
    rodadas: Annotated[
        int,
        typer.Option(
            min=0,
            help="Rodadas extras para datasets adiados por timeout ou falha transitória "
            "(0 desliga o adiamento).",
        ),
    ] = 2,
    tentativas_iniciais: Annotated[
        int, typer.Option(min=1, help="Tentativas por requisição antes de adiar o dataset.")
    ] = 2,
    pausa: Annotated[float, typer.Option(min=0, help="Pausa (s) entre as rodadas.")] = 60.0,
) -> None:
    """Executa a ingestão. Um dataset com falha não impede os demais.

    Um dataset com timeout vai para o fim da fila e é tentado de novo depois dos
    demais, reaproveitando os períodos já baixados nesta execução. A última
    rodada usa as tentativas normais da fonte.
    """
    rt = _runtime(_settings())
    targets = [d.id for d in rt.catalog.datasets.values() if d.enabled] if all_datasets else []
    targets += [d for d in dataset_ids or [] if d not in targets]
    if not targets:
        typer.echo("informe os datasets ou use --all", err=True)
        raise typer.Exit(code=2)
    for dataset_id in targets:
        rt.catalog.dataset(dataset_id)  # falha cedo para identificadores desconhecidos
    reports: list[dict[str, Any]] = []
    try:
        with tracked_run(
            rt.engine, "ingest.run", rt.settings.code_version, {"datasets": targets, "full": full}
        ) as run_id:
            for report in rt.runner.run_many(
                targets,
                run_id=run_id,
                full=full,
                defer_rounds=rodadas,
                first_pass_attempts=tentativas_iniciais,
                pause_s=pausa,
            ):
                reports.append(asdict(report))
            failed = [r["dataset_id"] for r in reports if r["status"] != "succeeded"]
            if failed:
                msg = f"datasets com falha: {failed}"
                raise IngestionFailedError(msg)
    except IngestionFailedError:
        _echo_json(reports)
        raise typer.Exit(code=1) from None
    finally:
        rt.engine.dispose()
    _echo_json(reports)


@ingest_app.command("status")
def ingest_status(
    dataset_id: Annotated[str | None, typer.Argument()] = None,
    limit: int = 10,
) -> None:
    """Últimas ingestões registradas."""
    settings = _settings()
    engine = make_engine(settings, pool_size=1)
    try:
        rows = PostgresIngestionRegistry(engine).recent_ingestions(dataset_id, limit)
    finally:
        engine.dispose()
    for r in rows:
        counts = (r["stats"] or {}).get("counts", {})
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "-"
        typer.echo(
            f"{r['started_at']:%Y-%m-%d %H:%M:%S} {r['status']:9} {r['dataset_id']:18} "
            f"{summary}{'  erro: ' + r['error'][:120] if r['error'] else ''}"
        )
