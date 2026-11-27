"""Prepara complemento rastreável da lente C, validado e sem ativação (ADR-0045).

Reutiliza o manifesto base e confere, por chave original, todas as fases e contagens.
A execução exige as permissões usuais do worker; não captura nem apaga originais.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from dataclasses import replace
from typing import Any

import polars as pl
from sqlalchemy import Engine

from odb_catalog import PostgresAdvisoryLock, PublicationService, TableVersion, make_engine
from odb_catalog.gold import PostgresGoldRegistry
from odb_catalog.publication import Release
from odb_common.settings import Settings, load_settings
from odb_common.storage import LakehouseLayout, Layer
from odb_ingestion import load_sources
from odb_lakehouse import DeltaReader, DeltaWriter
from odb_modeling import contas
from odb_modeling.builder import GoldBuild, GoldTable
from odb_modeling.contas_builder import _EXECUTION_COLUMNS
from odb_modeling.contas_locations import (
    FACT_EXECUTION_LOCATION,
    LOCATION_FIELDS,
    execution_locations,
    reconcile_locations,
)
from odb_modeling.quality import table_checks
from odb_processing.quality import CheckResult, CheckStatus, blocking
from odb_processing.silver import PreviousRun


def _materialize(
    base: Release,
    run: PreviousRun,
    build: GoldBuild,
    settings: Settings,
    engine: Engine,
) -> dict[str, Any]:
    """Materializa só o novo fato e confere todos os grãos da candidata base."""
    if run.delta_version is None:
        msg = "versão Silver não fixada"
        raise ValueError(msg)
    reader = DeltaReader()
    evidence: list[dict[str, Any]] = []

    def read(name: str) -> pl.LazyFrame:
        table = base.tables[name]
        return reader.scan(table.storage_uri, table.delta_version)

    dims = contas.Dimensions(
        recipient=pl.DataFrame(),
        management_unit=read("dim_management_unit").collect(),
        budget_action=read("dim_budget_action").collect(),
        expense_nature=read("dim_expense_nature").collect(),
        amendment_author=read("dim_amendment_author").collect(),
    )
    silver = reader.scan(run.target_uri, run.delta_version).select(
        *_EXECUTION_COLUMNS, *LOCATION_FIELDS
    )
    periods = silver.select(contas.gold_period()).unique().collect()["period"].sort().to_list()
    old = read("fact_federal_budget_execution")
    old_periods = old.select("period").unique().collect()["period"].sort().to_list()
    if periods != old_periods:
        msg = "calendário da Silver não coincide com o release base"
        raise ValueError(msg)
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    writer = DeltaWriter(
        layout,
        PostgresAdvisoryLock(engine),
        disk_warn_percent=settings.disk_warn_percent,
        disk_block_percent=settings.disk_block_percent,
    )
    contract = FACT_EXECUTION_LOCATION
    uri = layout.table_uri(Layer.GOLD, "contas", contract.name)
    version = None
    count = 0
    for year in sorted({p[:4] for p in periods}):
        located = execution_locations(silver.filter(pl.col("period").str.starts_with(year)), dims)
        original = old.filter(pl.col("year") == int(year)).collect()
        equal = reconcile_locations(located, original)
        build.checks.append(
            CheckResult(
                f"localizadores.fidelidade_{year}",
                CheckStatus.PASS if equal else CheckStatus.FAIL,
                "todas as chaves originais, seis fases e contagem de linhas",
                observed=located.height,
            )
        )
        build.checks.extend(
            replace(check, check_id=f"{check.check_id}.{year}")
            for check in table_checks(contract.name, located, contract)
        )
        if blocking(build.checks):
            msg = f"reconciliação ou contrato falhou em {year}; candidata não publicável"
            raise ValueError(msg)
        version = writer.write(
            uri,
            located,
            run_id=build.build_id,
            mode="overwrite" if version is None else "append",
            partition_by=contract.partition_by,
        ).version
        count += located.height
        coverage = (
            located.group_by("period", "location_uf")
            .agg(*(pl.col(name).sum() for name in contas.EXECUTION_MEASURES))
            .sort("period", "location_uf", nulls_last=True)
        )
        evidence.append(
            {
                "year": year,
                "rows": located.height,
                "old_rows": original.height,
                "equal": equal,
                "coverage": coverage.to_dicts(),
            }
        )
    if version is None:
        msg = "nenhum período de execução"
        raise ValueError(msg)
    build.tables = {
        name: GoldTable(name, t.storage_uri, t.delta_version, t.contract_version)
        for name, t in base.tables.items()
    }
    build.tables[contract.name] = GoldTable(contract.name, uri, version, contract.version, count)
    return {
        "periods": periods,
        "evidence": evidence,
        "table": {"uri": uri, "delta_version": version, "rows": count},
    }


def prepare(base_id: str) -> dict[str, Any]:
    """Cria uma candidata complementar somente após reconciliação integral da lente C."""
    settings = load_settings()
    engine = make_engine(settings, pool_size=3)
    reader = DeltaReader()
    publication = PublicationService(engine, reader, actor="odb-localizadores")
    registry = PostgresGoldRegistry(engine)
    base = publication.get(base_id)
    if base.scope != "contas" or base.status not in {"validated", "active", "superseded"}:
        msg = "a base precisa ser um release validado das contas"
        raise ValueError(msg)
    sources = load_sources(settings.sources_config_dir)
    datasets = [
        d.id
        for d in sources.datasets.values()
        if d.silver.get("transformer") == "cgu_budget_execution"
    ]
    if len(datasets) != 1:
        msg = "esperado um único dataset oficial da execução"
        raise ValueError(msg)
    run = registry.silver_success(datasets[0])
    if run is None or run.delta_version is None:
        msg = "Silver da execução não disponível"
        raise ValueError(msg)
    inputs = {
        "base_release": base_id,
        "execution": {
            "dataset_id": datasets[0],
            "run_id": run.run_id,
            "uri": run.target_uri,
            "delta_version": run.delta_version,
        },
    }
    build = GoldBuild(
        str(uuid.uuid4()),
        "contas",
        "contas-localizadores@1.0.0",
        settings.code_version,
        inputs=inputs,
    )
    build.input_fingerprint = hashlib.sha256(
        json.dumps(inputs, sort_keys=True).encode()
    ).hexdigest()
    registry.start_build(build, pipeline_run_id=None)
    try:
        materialized = _materialize(base, run, build, settings, engine)
        build.status = "succeeded"
    except Exception as exc:
        build.status = "failed"
        build.error = str(exc)
        raise
    finally:
        registry.record_checks(build.build_id, build.scope, build.checks)
        registry.finish_build(build)
    try:
        release_id = publication.create_draft(
            "contas",
            settings.code_version,
            [
                TableVersion(t.table_id, t.storage_uri, t.delta_version, t.contract_version)
                for t in build.tables.values()
            ],
        )
        registry.link_release(build.build_id, release_id)
        candidate = publication.validate(release_id)
        return {
            "build_id": build.build_id,
            "release_id": candidate.release_id,
            "status": candidate.status,
            "base_release": base_id,
            "inputs": inputs,
            **materialized,
        }
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-release", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.base_release), ensure_ascii=False, indent=2, default=str))
