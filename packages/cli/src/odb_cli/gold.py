"""Comandos `odb gold`, `odb release`, `odb indicators` e `odb query`."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from decimal import Decimal
from typing import Annotated, Any

import polars as pl
import typer

from odb_catalog import (
    PostgresAdvisoryLock,
    PublicationError,
    PublicationService,
    Release,
    TableVersion,
    make_engine,
    tracked_run,
)
from odb_catalog.gold import PostgresGoldRegistry
from odb_catalog.ingestion import PostgresIngestionRegistry
from odb_common.logging import configure_logging
from odb_common.settings import Settings, load_settings
from odb_common.storage import LakehouseLayout, Layer
from odb_ingestion import load_sources
from odb_lakehouse import DeltaReader, DeltaWriter
from odb_modeling.builder import GoldBuild, GoldBuilder
from odb_modeling.contracts import DIM_INDICATOR, DIM_INDICATOR_NODE
from odb_query_engine import DuckDBConfig, DuckDBReadEngine, PinnedTable, QueryError, ReadQuery
from odb_semantics import IndicatorQuery, SemanticError, load_scope, meta_from_rows, plan_query

DEFAULT_SCOPE = "demografia"

gold_app = typer.Typer(no_args_is_help=True, help="Camada Gold (Delta Lake) e publicação.")
release_app = typer.Typer(no_args_is_help=True, help="Releases publicados (PostgreSQL).")
indicators_app = typer.Typer(no_args_is_help=True, help="Catálogo de indicadores publicados.")


def _settings() -> Settings:
    settings = load_settings()
    configure_logging(settings.log_level)
    return settings


def _echo_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _publication(settings: Settings, engine: Any) -> PublicationService:
    return PublicationService(engine, DeltaReader(), actor=f"odb-cli:{settings.code_version}")


def _release_json(release: Release) -> dict[str, Any]:
    return {
        "release_id": release.release_id,
        "scope": release.scope,
        "status": release.status,
        "activated_at": release.activated_at,
        "failure_reason": release.failure_reason,
        "tables": {t.table_id: t.delta_version for t in release.tables.values()},
    }


def _summary(build: GoldBuild) -> dict[str, Any]:
    return {
        "build_id": build.build_id,
        "scope": build.scope,
        "status": build.status,
        "tables": {t.table_id: t.delta_version for t in build.tables.values()},
        "rows": build.stats()["rows"],
        "checks": build.stats()["checks"],
        "warnings": build.warnings(),
        "error": build.error,
    }


def _same_versions(release: Release | None, build: GoldBuild) -> bool:
    if release is None:
        return False
    return {t: v.delta_version for t, v in release.tables.items()} == {
        t: v.delta_version for t, v in build.tables.items()
    }


# ------------------------------------------------------------------ gold


@gold_app.command("build")
def gold_build(
    scope: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
    force: Annotated[bool, typer.Option(help="Reconstrói mesmo sem mudança na Silver.")] = False,
    activate: Annotated[
        bool, typer.Option(help="Ativa o release validado (publicação interna).")
    ] = False,
) -> None:
    """Constrói a Gold, cria e valida um release e, com --activate, publica."""
    settings = _settings()
    sources = load_sources(settings.sources_config_dir)
    catalog = load_scope(settings.indicators_config_dir, scope)
    engine = make_engine(settings, pool_size=3)
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    writer = DeltaWriter(
        layout,
        PostgresAdvisoryLock(engine),
        disk_warn_percent=settings.disk_warn_percent,
        disk_block_percent=settings.disk_block_percent,
    )
    registry = PostgresGoldRegistry(engine)
    builder = GoldBuilder(
        sources, catalog, layout, writer, registry, code_version=settings.code_version
    )
    PostgresIngestionRegistry(engine).sync_catalog(sources)
    publication = _publication(settings, engine)
    output: dict[str, Any] = {}
    try:
        with tracked_run(
            engine,
            "gold.build",
            settings.code_version,
            {"scope": scope, "force": force, "activate": activate},
        ) as run_id:
            build = builder.build(pipeline_run_id=run_id, force=force)
            output.update(_summary(build))
            if build.status == "failed":
                active = publication.active(scope)
                output["active_release"] = active.release_id if active else None
                msg = f"construção Gold falhou: {build.error}"
                raise GoldFailedError(msg)
            indicators = build.tables[DIM_INDICATOR.name]
            registry.sync_indicators(
                scope,
                catalog.config_version,
                build.build_id,
                DeltaReader().scan(indicators.storage_uri, indicators.delta_version).collect(),
            )
            output["release"] = _publish(publication, registry, build, settings, activate=activate)
    except PublicationError as exc:
        output["publication_error"] = str(exc)
        _echo_json(output)
        raise typer.Exit(code=1) from None
    except GoldFailedError:
        _echo_json(output)
        raise typer.Exit(code=1) from None
    finally:
        engine.dispose()
    _echo_json(output)


class GoldFailedError(RuntimeError):
    """A construção Gold falhou; o release vigente foi preservado."""


def _publish(
    publication: PublicationService,
    registry: PostgresGoldRegistry,
    build: GoldBuild,
    settings: Settings,
    *,
    activate: bool,
) -> dict[str, Any]:
    """Cria e valida o release da construção; com ``activate``, publica."""
    active = publication.active(build.scope)
    if active is not None and _same_versions(active, build):
        return {**_release_json(active), "note": "release ativo já referencia estas versões"}
    release_id = publication.create_draft(
        build.scope,
        settings.code_version,
        [
            TableVersion(
                table_id=t.table_id,
                storage_uri=t.storage_uri,
                delta_version=t.delta_version,
                contract_version=t.contract_version,
                quality_status="passed",
            )
            for t in build.tables.values()
        ],
    )
    registry.link_release(build.build_id, release_id)
    release = publication.validate(release_id)
    if activate:
        release = publication.activate(release_id)
    return _release_json(release)


# ------------------------------------------------------------------ release


@release_app.command("list")
def release_list(
    scope: Annotated[str | None, typer.Option(help="Filtra por escopo.")] = None,
    limit: Annotated[int, typer.Option(min=1, max=200)] = 20,
) -> None:
    """Releases mais recentes."""
    settings = _settings()
    engine = make_engine(settings, pool_size=1)
    try:
        releases = _publication(settings, engine).list_releases(scope, limit)
    finally:
        engine.dispose()
    _echo_json([_release_json(r) for r in releases])


@release_app.command("activate")
def release_activate(release_id: str) -> None:
    """Ativa um release validado. O anterior do escopo vira ``superseded``."""
    settings = _settings()
    engine = make_engine(settings, pool_size=1)
    try:
        release = _publication(settings, engine).activate(release_id)
    except PublicationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
    finally:
        engine.dispose()
    _echo_json(_release_json(release))


# ------------------------------------------------------------------ consulta


@contextmanager
def _released(settings: Settings, scope: str) -> Iterator[tuple[Release, DuckDBReadEngine]]:
    """Release ativo do escopo e motor DuckDB restrito à Gold."""
    engine = make_engine(settings, pool_size=1)
    try:
        release = _publication(settings, engine).active(scope)
    finally:
        engine.dispose()
    if release is None:
        typer.echo(f"nenhum release ativo no escopo {scope!r}", err=True)
        raise typer.Exit(code=1)
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    duck = DuckDBReadEngine(DuckDBConfig.from_settings(settings), [layout.layer_uri(Layer.GOLD)])
    try:
        yield release, duck
    finally:
        duck.close()


def _pinned(release: Release, table_id: str) -> PinnedTable:
    try:
        table = release.tables[table_id]
    except KeyError:
        typer.echo(f"tabela {table_id} ausente do release {release.release_id}", err=True)
        raise typer.Exit(code=1) from None
    return PinnedTable(table.storage_uri, table.delta_version)


def _dicts(columns: Sequence[str], rows: Sequence[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [dict(zip(columns, r, strict=True)) for r in rows]


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        text = format(value.normalize(), "f")
        return text
    return str(value)


@indicators_app.command("list")
def indicators_list(
    scope: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
    as_json: Annotated[bool, typer.Option("--json", help="Saída em JSON.")] = False,
) -> None:
    """Indicadores do release ativo, com níveis e períodos disponíveis."""
    settings = _settings()
    with _released(settings, scope) as (release, duck):
        result = duck.execute(
            ReadQuery(
                "SELECT indicator_id, name, unit, additivity, available_levels, periods, "
                "classification_ids, dataset_id FROM {{ind}} ORDER BY node_key",
                {"ind": _pinned(release, DIM_INDICATOR.name)},
            )
        )
    rows = _dicts(result.columns, result.rows)
    if as_json:
        _echo_json({"release_id": release.release_id, "indicators": rows})
        return
    for r in rows:
        periods = r["periods"]
        span = f"{periods[0]}..{periods[-1]}" if len(periods) > 1 else ",".join(periods)
        typer.echo(
            f"{r['indicator_id']:40} {r['unit']:12} {span:10} "
            f"níveis={','.join(r['available_levels'])} "
            f"classificações={','.join(r['classification_ids']) or '-'}"
        )


@indicators_app.command("tree")
def indicators_tree(
    scope: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
) -> None:
    """Árvore temática: grupo → indicador → classificação → categoria."""
    settings = _settings()
    with _released(settings, scope) as (release, duck):
        result = duck.execute(
            ReadQuery(
                "SELECT depth, node_type, label, indicator_id, classification_id, category_key "
                "FROM {{nodes}} ORDER BY sort_order",
                {"nodes": _pinned(release, DIM_INDICATOR_NODE.name)},
                max_rows=10_000,
            )
        )
    for r in _dicts(result.columns, result.rows):
        ref = ""
        if r["node_type"] == "indicator":
            ref = f"  [{r['indicator_id']}]"
        elif r["node_type"] == "classification":
            ref = f"  [--by {r['classification_id']}]"
        elif r["node_type"] == "category":
            ref = f"  [{r['category_key'].replace(':', '=', 1)}]"
        typer.echo(f"{'  ' * int(r['depth'])}{r['label']}{ref}")


def _parse_breakdown(values: Sequence[str]) -> dict[str, tuple[str, ...] | None]:
    out: dict[str, tuple[str, ...] | None] = {}
    for item in values:
        cid, _, cats = item.partition("=")
        out[cid.strip()] = tuple(c.strip() for c in cats.split(",")) if cats else None
    return out


def query_command(  # noqa: PLR0917 - opções da CLI (typer)
    indicator: Annotated[
        list[str], typer.Option("--indicator", "-i", help="Indicador (repetível).")
    ],
    level: Annotated[str, typer.Option(help="Nível territorial do resultado.")] = "uf",
    within: Annotated[
        str | None, typer.Option(help="Recorte territorial, por exemplo uf:29.")
    ] = None,
    period: Annotated[list[str] | None, typer.Option("--period", "-p", help="Período.")] = None,
    by: Annotated[
        list[str] | None,
        typer.Option(help="Desagregação: c86 (todas as categorias) ou c86=2779,2780."),
    ] = None,
    sum_to: Annotated[
        str | None, typer.Option(help="Soma os territórios do nível até este nível (derivado).")
    ] = None,
    scope: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
    output: Annotated[str, typer.Option("--format", help="table, json ou csv.")] = "table",
    limit: Annotated[int, typer.Option(min=1, max=100_000)] = 1000,
) -> None:
    """Consulta indicadores no release ativo (DuckDB sobre a Gold publicada)."""
    settings = _settings()
    query = IndicatorQuery(
        indicators=tuple(indicator),
        level=level,
        within=within,
        periods=tuple(period or ()),
        breakdown=_parse_breakdown(by or []),
        sum_to=sum_to,
    )
    with _released(settings, scope) as (release, duck):
        meta_result = duck.execute(
            ReadQuery(
                "SELECT * FROM {{ind}} WHERE list_contains(CAST($ids AS VARCHAR[]), indicator_id)",
                {"ind": _pinned(release, DIM_INDICATOR.name)},
                params={"ids": list(query.indicators)},
            )
        )
        meta = meta_from_rows(_dicts(meta_result.columns, meta_result.rows))
        try:
            plan = plan_query(query, meta)
        except SemanticError as exc:
            typer.echo(f"consulta rejeitada: {exc}", err=True)
            raise typer.Exit(code=2) from None
        try:
            result = duck.execute(
                ReadQuery(
                    plan.sql_template,
                    {alias: _pinned(release, table) for alias, table in plan.aliases.items()},
                    params=plan.params,
                    max_rows=limit,
                )
            )
        except QueryError as exc:
            typer.echo(f"erro na consulta: {exc}", err=True)
            raise typer.Exit(code=1) from None
    rows = _dicts(result.columns, result.rows)
    provenance = {
        "release_id": release.release_id,
        "scope": scope,
        "tables": {a: f"{t.table_uri}@v{t.version}" for a, t in result.tables.items()},
        "derived": plan.derived,
        "truncated": result.truncated,
        "rows": len(rows),
    }
    if output == "json":
        _echo_json({"provenance": provenance, "warnings": list(plan.warnings), "rows": rows})
        return
    for w in plan.warnings:
        typer.echo(f"aviso: {w}", err=True)
    if output == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(result.columns)
        writer.writerows([[_fmt(v) for v in r] for r in result.rows])
        typer.echo(buffer.getvalue().rstrip("\n"))
        return
    frame = pl.DataFrame(
        [{k: _fmt(v) for k, v in r.items()} for r in rows],
        schema=dict.fromkeys(result.columns, pl.String),
    )
    with pl.Config(
        tbl_rows=limit, tbl_width_chars=200, fmt_str_lengths=60, tbl_hide_dataframe_shape=True
    ):
        typer.echo(frame)
    typer.echo(
        f"release {release.release_id} · {len(rows)} linhas"
        + (" (truncado)" if result.truncated else "")
        + (" · valores derivados por soma" if plan.derived else ""),
        err=True,
    )


def quality_gold(
    scope: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
    as_json: Annotated[bool, typer.Option("--json", help="Saída em JSON com detalhes.")] = False,
) -> None:
    """Resultados de qualidade da última construção Gold do escopo."""
    settings = _settings()
    engine = make_engine(settings, pool_size=1)
    try:
        build, checks = PostgresGoldRegistry(engine).latest_report(scope)
    finally:
        engine.dispose()
    if build is None:
        typer.echo(f"nenhum resultado de qualidade Gold para {scope}", err=True)
        raise typer.Exit(code=1)
    if as_json:
        _echo_json({"build": build, "checks": checks})
        return
    typer.echo(
        f"{scope}: construção {build['build_id']} ({build['status']}, release "
        f"{build['release_id'] or '-'}) em {build['started_at']:%Y-%m-%d %H:%M:%S}"
    )
    for c in checks:
        typer.echo(f"  [{c['status'].upper():4}] {c['check_id']:70} {c['message']}")


__all__ = ["gold_app", "indicators_app", "quality_gold", "query_command", "release_app"]
