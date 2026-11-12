"""Construção da Gold de um escopo (§10).

Fluxo de ``GoldBuilder.build()``:

1. resolve as versões Silver vigentes (última execução válida de cada dataset)
   e calcula a impressão digital: versões Silver + catálogo semântico +
   contratos. Se for igual à da última construção bem-sucedida e as versões
   Gold ainda existirem, a execução termina ``skipped``;
2. lê a Silver nas versões fixadas e confere o catálogo contra os dados
   (unidades, níveis, classificações, categorias e notas oficiais);
3. monta dimensões, estrutura universal e fatos temáticos (Polars);
4. roda as verificações. Um ``fail`` bloqueia tudo: nenhuma tabela é escrita;
5. confere o schema de cada tabela existente. Uma mudança incompatível
   bloqueia antes de qualquer escrita;
6. grava cada tabela por inteiro (``overwrite``) e registra as versões.

A escrita não publica nada. A publicação é feita depois, por release
(``odb_catalog.publication``), e um release só referencia versões completas.
Se uma escrita falhar no meio, as tabelas já gravadas têm versões novas que
nenhum release referencia, e o release vigente continua íntegro.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import polars as pl
from deltalake import DeltaTable

from odb_common.logging import log_context
from odb_common.storage import LakehouseLayout, Layer
from odb_ingestion.config import SourceCatalog
from odb_ingestion.connectors.sidra import SidraConnector
from odb_lakehouse import DeltaReader, DeltaWriter
from odb_modeling import model
from odb_modeling.contracts import (
    BRIDGE_GEOGRAPHY_ANCESTOR,
    DIM_BREAKDOWN,
    DIM_CATEGORY,
    DIM_CLASSIFICATION,
    DIM_GEOGRAPHY,
    DIM_GEOMETRY,
    DIM_INDICATOR,
    DIM_INDICATOR_NODE,
    DIM_PERIOD,
    FIXED_CONTRACTS,
    INDICATOR_OBSERVATION,
    fact_contract,
)
from odb_modeling.geography import GeographyError, build_ancestor_bridge, build_dim_geography
from odb_modeling.geometry import GeometryError, build_dim_geometry
from odb_modeling.quality import (
    category_reconciliation,
    consistency_checks,
    foreign_key,
    geography_checks,
    geometry_checks,
    input_checks,
    silver_fidelity,
    table_checks,
)
from odb_processing.contracts import SIDRA_OBSERVATION, Contract, SchemaChange, compare_schema
from odb_processing.quality import CheckResult, blocking
from odb_processing.silver import PreviousRun
from odb_semantics import SemanticCatalog

logger = logging.getLogger(__name__)

# Versão das regras de modelagem. Sobe quando a transformação muda sem mudar
# contratos nem catálogo, para forçar a reconstrução.
MODEL_VERSION = "1.2.0"
GoldStatus = Literal["running", "succeeded", "skipped", "failed"]


class GoldBuildError(RuntimeError):
    """Falha que impede a construção da Gold."""


@dataclass(frozen=True, slots=True)
class GoldTable:
    """Versão de uma tabela Gold produzida (ou reutilizada) por uma construção."""

    table_id: str
    storage_uri: str
    delta_version: int
    contract_version: str
    rows: int | None = None


@dataclass(frozen=True, slots=True)
class PreviousGoldBuild:
    """Última construção bem-sucedida de um escopo."""

    build_id: str
    input_fingerprint: str
    tables: Mapping[str, GoldTable]


class GoldRegistry(Protocol):
    """Persistência das construções Gold (implementação: ``odb_catalog.gold``)."""

    def silver_success(self, dataset_id: str) -> PreviousRun | None:
        """Última execução Silver válida do dataset."""
        ...

    def last_success(self, scope: str) -> PreviousGoldBuild | None:
        """Última construção Gold ``succeeded`` ou ``skipped`` do escopo."""
        ...

    def start_build(self, build: GoldBuild, *, pipeline_run_id: str | None) -> None:
        """Registra a construção como ``running``."""
        ...

    def finish_build(self, build: GoldBuild) -> None:
        """Finaliza com estado, tabelas e estatísticas."""
        ...

    def record_checks(self, build_id: str, scope: str, results: Sequence[CheckResult]) -> None:
        """Grava os resultados de qualidade."""
        ...


@dataclass
class GoldBuild:
    """Estado e resultado de uma construção Gold."""

    build_id: str
    scope: str
    config_version: str
    code_version: str
    input_fingerprint: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    status: GoldStatus = "running"
    tables: dict[str, GoldTable] = field(default_factory=dict)
    checks: list[CheckResult] = field(default_factory=list)
    error: str | None = None

    def stats(self) -> dict[str, Any]:
        """Estatísticas da construção."""
        counts: dict[str, int] = {}
        for c in self.checks:
            counts[c.status.value] = counts.get(c.status.value, 0) + 1
        return {
            "checks": counts,
            "rows": {t.table_id: t.rows for t in self.tables.values() if t.rows is not None},
        }

    def warnings(self) -> list[str]:
        """Identificadores das verificações com aviso."""
        return [c.check_id for c in self.checks if c.status.value == "warn"]


class GoldBuilder:
    """Constrói as tabelas Gold de um escopo a partir da Silver vigente."""

    def __init__(
        self,
        sources: SourceCatalog,
        catalog: SemanticCatalog,
        layout: LakehouseLayout,
        writer: DeltaWriter,
        registry: GoldRegistry,
        *,
        code_version: str = "unknown",
    ) -> None:
        """Recebe as fontes, o catálogo semântico, o lakehouse, o escritor e o registro."""
        self._sources = sources
        self._catalog = catalog
        self._layout = layout
        self._writer = writer
        self._registry = registry
        self._code_version = code_version
        self._reader = DeltaReader()

    # ------------------------------------------------------------- configuração

    def table_uri(self, table_id: str) -> str:
        """URI de uma tabela Gold do escopo."""
        return self._layout.table_uri(Layer.GOLD, self._catalog.scope, table_id)

    def series_members(self, dataset_id: str) -> list[str]:
        """Datasets de uma série (``silver.series``), ordenados; vazio se não for série.

        Uma série reúne datasets que publicam a mesma tabela em arquivos separados (o
        Sinesp VDE tem um dataset por ano): o catálogo semântico aponta para a série.
        """
        return sorted(
            d
            for d in self._sources.datasets
            if self._sources.dataset(d).silver.get("series") == dataset_id
        )

    def _member_datasets(self, dataset_id: str) -> list[str]:
        return self.series_members(dataset_id) or [dataset_id]

    def datasets(self) -> dict[str, model.DatasetInfo]:
        """Datasets do catálogo, com tabela de origem, URL e licença."""
        out: dict[str, model.DatasetInfo] = {}
        for dataset_id in self._catalog.datasets():
            members = self.series_members(dataset_id)
            if members:
                out[dataset_id] = self._series_info(dataset_id, members)
                continue
            dataset = self._sources.dataset(dataset_id)
            if dataset.silver.get("transformer") != "sidra_observation":
                msg = f"{dataset_id}: a Gold desta versão aceita apenas datasets SIDRA"
                raise GoldBuildError(msg)
            params = SidraConnector.params(dataset)
            out[dataset_id] = model.DatasetInfo(
                dataset_id=dataset_id,
                table_id=params.table,
                reference_url=dataset.reference_url,
                license_id=dataset.license,
                period_type=params.period_type,
            )
        return out

    def _series_info(self, series_id: str, members: list[str]) -> model.DatasetInfo:
        """Série de planilhas anuais do Sinesp VDE (uma tabela Silver por ano)."""
        configs = [self._sources.dataset(m) for m in members]
        if {c.silver.get("transformer") for c in configs} != {"sinesp_vde"}:
            msg = f"{series_id}: a Gold desta versão aceita séries só do Sinesp VDE"
            raise GoldBuildError(msg)
        if len({c.license for c in configs}) != 1:
            msg = f"{series_id}: membros da série com licenças diferentes"
            raise GoldBuildError(msg)
        base = str(configs[0].silver.get("table_id", "SINESP-VDE"))
        return model.DatasetInfo(
            dataset_id=series_id,
            table_id=base,
            reference_url=configs[0].reference_url,
            license_id=configs[0].license,
            period_type="mes",
            table_ids=tuple(f"{base}-{c.params['reference_period']}" for c in configs),
        )

    def reference_dataset(self) -> str:
        """Referência territorial comum dos datasets (DTB)."""
        refs = {
            str(self._sources.dataset(m).silver.get("territorial_reference"))
            for d in self._catalog.datasets()
            for m in self._member_datasets(d)
        }
        if len(refs) != 1 or "None" in refs:
            msg = f"os datasets precisam de uma única referência territorial: {sorted(refs)}"
            raise GoldBuildError(msg)
        return refs.pop()

    def contracts(self) -> dict[str, Contract]:
        """Contratos de todas as tabelas do escopo."""
        flagged = {n.dataset for n in self._catalog.pending_installation}
        contracts = {c.name: c for c in FIXED_CONTRACTS}
        for fact in self._catalog.facts:
            contracts[fact.id] = fact_contract(self._catalog, fact, flags=fact.dataset in flagged)
        if self._catalog.geometry:
            contracts[DIM_GEOMETRY.name] = DIM_GEOMETRY
        return contracts

    # ------------------------------------------------------------- execução

    def build(self, *, pipeline_run_id: str | None = None, force: bool = False) -> GoldBuild:
        """Constrói a Gold. Erros ficam registrados no ``GoldBuild``."""
        build = GoldBuild(
            build_id=str(uuid.uuid4()),
            scope=self._catalog.scope,
            config_version=self._catalog.config_version,
            code_version=self._code_version,
        )
        with log_context(gold_build_id=build.build_id, scope=build.scope):
            try:
                inputs = self._resolve_inputs()
                build.inputs = inputs
                build.input_fingerprint = self._fingerprint(inputs)
            except Exception as exc:
                build.status = "failed"
                build.error = f"{type(exc).__name__}: {exc}"
                build.input_fingerprint = "0" * 64
            self._registry.start_build(build, pipeline_run_id=pipeline_run_id)
            try:
                if build.status != "failed":
                    self._execute(build, force=force)
            except Exception as exc:
                build.status = "failed"
                build.error = f"{type(exc).__name__}: {exc}"
                logger.exception("gold build failed")
            finally:
                if build.checks:
                    self._registry.record_checks(build.build_id, build.scope, build.checks)
                self._registry.finish_build(build)
        return build

    def _silver(self, dataset_id: str) -> PreviousRun:
        run = self._registry.silver_success(dataset_id)
        if run is None or run.delta_version is None:
            msg = f"Silver sem execução válida para {dataset_id}; execute `odb silver build`"
            raise GoldBuildError(msg)
        return run

    def _resolve_inputs(self) -> dict[str, Any]:
        runs = {
            m: self._silver(m) for d in self._catalog.datasets() for m in self._member_datasets(d)
        }
        # Uma ou mais tabelas Silver (IBGE, MJSP...), cada uma na versão mais recente
        # entre os seus datasets: cada build Silver substitui só a própria partição.
        silver: dict[str, int] = {}
        for run in runs.values():
            silver[run.target_uri] = max(silver.get(run.target_uri, 0), int(run.delta_version or 0))
        reference = self.reference_dataset()
        ref_run = self._silver(reference)
        geometry: dict[str, Any] = {}
        meshes = {d: self._silver(d) for d in self._catalog.geometry_datasets()}
        if meshes:
            mesh_uris = {r.target_uri for r in meshes.values()}
            if len(mesh_uris) != 1:
                msg = f"malhas em tabelas Silver diferentes: {sorted(mesh_uris)}"
                raise GoldBuildError(msg)
            geometry = {
                "uri": mesh_uris.pop(),
                "silver_version": max(int(r.delta_version or 0) for r in meshes.values()),
                "datasets": {
                    d: {"run_id": r.run_id, "delta_version": r.delta_version}
                    for d, r in sorted(meshes.items())
                },
            }
        # Cada build Silver substitui só a partição do próprio dataset: a versão
        # mais recente contém o estado vigente de todos.
        return {
            "geometry": geometry,
            "silver": dict(sorted(silver.items())),
            "datasets": {
                d: {"run_id": r.run_id, "delta_version": r.delta_version, "uri": r.target_uri}
                for d, r in sorted(runs.items())
            },
            "reference": {
                "dataset_id": reference,
                "uri": ref_run.target_uri,
                "delta_version": ref_run.delta_version,
            },
        }

    def _fingerprint(self, inputs: Mapping[str, Any]) -> str:
        payload = {
            "model_version": MODEL_VERSION,
            "catalog": self._catalog.content_sha256,
            "contracts": {n: c.version for n, c in sorted(self.contracts().items())},
            "silver_contract": SIDRA_OBSERVATION.version,
            "inputs": inputs,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _unchanged(self, build: GoldBuild) -> PreviousGoldBuild | None:
        previous = self._registry.last_success(build.scope)
        if previous is None or previous.input_fingerprint != build.input_fingerprint:
            return None
        expected = set(self.contracts())
        if set(previous.tables) != expected:
            return None
        if all(
            self._reader.has_version(t.storage_uri, t.delta_version)
            for t in previous.tables.values()
        ):
            return previous
        return None

    def _execute(self, build: GoldBuild, *, force: bool) -> None:
        previous = None if force else self._unchanged(build)
        if previous is not None:
            build.status = "skipped"
            build.tables = dict(previous.tables)
            logger.info("gold unchanged", extra={"previous_build": previous.build_id})
            return
        frames = self._frames(build)
        failures = blocking(build.checks)
        if failures:
            msg = "verificações bloqueantes falharam: " + ", ".join(c.check_id for c in failures)
            raise GoldBuildError(msg)
        self._write(build, frames)
        build.status = "succeeded"

    def _frames(self, build: GoldBuild) -> dict[str, pl.DataFrame]:
        inputs = build.inputs
        datasets = self.datasets()
        mapping = model.indicator_map(self._catalog, datasets)
        # Memória (KI-007): só as colunas que a Gold usa e só as variáveis do
        # catálogo são materializadas; os nomes municipais vêm num recorte à parte.
        scan = self._silver_scan(inputs, datasets)
        names = model.municipal_names(scan)
        silver = scan.join(
            mapping.lazy().select("table_id", "variable_id").unique(),
            on=["table_id", "variable_id"],
            how="semi",
        ).collect()
        selected, fixed_problems = model.strip_fixed_categories(
            model.select_silver(silver, mapping, self._catalog), self._catalog
        )
        del silver
        pending, pending_report = model.resolve_pending_installation(self._catalog, names, datasets)
        build.checks = input_checks(
            selected, self._catalog, datasets, pending_report, fixed_problems
        )
        if blocking(build.checks):
            return {}

        ref = inputs["reference"]
        dtb_all = self._reader.scan(ref["uri"], int(ref["delta_version"])).collect()
        year = str(dtb_all["reference_year"].max())
        dtb = dtb_all.filter(pl.col("reference_year") == year)

        observations = model.build_observations(
            selected,
            self._catalog,
            silver_version=self._silver_versions(inputs, datasets),
            build_id=build.build_id,
            pending=pending,
            period_types={d.dataset_id: d.period_type for d in datasets.values()},
        )
        # Territórios observados, com o nome do período mais recente.
        observed = (
            selected.sort("period", descending=True)
            .select(
                pl.col("territorial_level")
                .replace_strict(model.SIDRA_LEVELS, default=None)
                .alias("level_id"),
                pl.col("territory_id").alias("code"),
                pl.col("territory_name").alias("name"),
            )
            .unique(["level_id", "code"], keep="first")
        )
        try:
            geography = build_dim_geography(
                dtb,
                observed,
                reference=f"{ref['dataset_id']} {year} (Silver v{ref['delta_version']})",
                uf_abbreviations=model.uf_abbreviations(names),
            )
            bridge = build_ancestor_bridge(geography)
        except GeographyError as exc:
            raise GoldBuildError(str(exc)) from exc

        used = sorted({cid for f in self._catalog.facts for cid in f.classifications})
        category_names = model.category_names(selected, self._catalog)
        categories = model.build_dim_category(self._catalog, used, category_names)
        geometry_results: list[CheckResult] = []
        extra: dict[str, pl.DataFrame] = {}
        if self._catalog.geometry:
            mesh_in = inputs["geometry"]
            mesh = (
                self._reader.scan(mesh_in["uri"], int(mesh_in["silver_version"]))
                .filter(pl.col("dataset_id").is_in(self._catalog.geometry_datasets()))
                .collect()
            )
            try:
                geometry, report = build_dim_geometry(
                    mesh,
                    geography,
                    bridge,
                    self._catalog.geometry,
                    silver_version=int(mesh_in["silver_version"]),
                )
            except GeometryError as exc:
                raise GoldBuildError(str(exc)) from exc
            extra[DIM_GEOMETRY.name] = geometry
            geometry_results = geometry_checks(geometry, report)
        frames: dict[str, pl.DataFrame] = {
            **extra,
            DIM_GEOGRAPHY.name: geography,
            BRIDGE_GEOGRAPHY_ANCESTOR.name: bridge,
            DIM_PERIOD.name: model.build_dim_period(observations),
            DIM_CLASSIFICATION.name: model.build_dim_classification(self._catalog, used),
            DIM_CATEGORY.name: categories,
            DIM_BREAKDOWN.name: model.build_dim_breakdown(observations, categories, self._catalog),
            DIM_INDICATOR.name: model.build_dim_indicator(
                self._catalog,
                observations,
                selected,
                datasets,
                model.indicator_node_keys(self._catalog),
            ),
            DIM_INDICATOR_NODE.name: model.build_dim_indicator_node(
                self._catalog, observations, categories
            ),
            INDICATOR_OBSERVATION.name: observations,
        }
        contracts = self.contracts()
        for fact in self._catalog.facts:
            frames[fact.id] = model.build_fact(
                observations, self._catalog, fact, contracts[fact.id]
            )
        build.checks.extend(self._checks(frames, selected, contracts))
        build.checks.extend(geometry_results)
        return frames

    def _silver_scan(
        self, inputs: Mapping[str, Any], datasets: Mapping[str, model.DatasetInfo]
    ) -> pl.LazyFrame:
        """Silvers de entrada (uma por fonte), projetadas e filtradas, ainda lazy.

        Nas séries (Sinesp), só entram as linhas nas categorias fixas dos fatos: a
        Silver traz o Total e cada dimensão, e a Gold desta versão usa só o Total.
        """
        uri_of = {m: str(info["uri"]) for m, info in inputs["datasets"].items()}
        tables: dict[str, list[str]] = {}
        for info in datasets.values():
            members = self.series_members(info.dataset_id) or [info.dataset_id]
            for member, table in zip(members, info.source_tables, strict=True):
                tables.setdefault(uri_of[member], []).append(table)
        scans = []
        for uri, version in inputs["silver"].items():
            scans.append(
                self._reader.scan(uri, int(version))
                .filter(pl.col("table_id").is_in(tables.get(uri, [])))
                .select(model.SILVER_COLUMNS)
            )
        scan = pl.concat(scans, how="vertical_relaxed")
        fixed = self._series_fixed_tables(datasets)
        if not fixed:
            return scan
        keep = ~pl.col("table_id").is_in([t for tables_ in fixed.values() for t in tables_])
        for codes, table_list in fixed.items():
            keep = keep | (
                pl.col("table_id").is_in(list(table_list))
                & pl.col("classifications")
                .list.eval(pl.element().struct.field("category_id").is_in(list(codes)))
                .list.all()
            )
        return scan.filter(keep)

    def _series_fixed_tables(
        self, datasets: Mapping[str, model.DatasetInfo]
    ) -> dict[frozenset[str], list[str]]:
        """Categorias fixas → tabelas das séries cujos fatos só fixam categorias."""
        out: dict[frozenset[str], list[str]] = {}
        for info in datasets.values():
            if not info.table_ids:
                continue
            facts = [f for f in self._catalog.facts if f.dataset == info.dataset_id]
            if not facts or any(f.classifications for f in facts):
                continue
            codes = frozenset(c for f in facts for c in f.fixed_categories.values())
            out.setdefault(codes, []).extend(info.table_ids)
        return out

    def _silver_versions(
        self, inputs: Mapping[str, Any], datasets: Mapping[str, model.DatasetInfo]
    ) -> dict[str, int]:
        """Versão da tabela Silver de cada dataset do catálogo (para a linhagem)."""
        versions = {str(uri): int(v) for uri, v in inputs["silver"].items()}
        out = {}
        for dataset_id in datasets:
            member = (self.series_members(dataset_id) or [dataset_id])[0]
            out[dataset_id] = versions[str(inputs["datasets"][member]["uri"])]
        return out

    def _checks(
        self,
        frames: Mapping[str, pl.DataFrame],
        selected: pl.DataFrame,
        contracts: Mapping[str, Contract],
    ) -> list[CheckResult]:
        results: list[CheckResult] = []
        for name, frame in frames.items():
            results.extend(table_checks(name, frame, contracts[name]))
        obs = frames[INDICATOR_OBSERVATION.name]
        geo = frames[DIM_GEOGRAPHY.name]
        cats = frames[DIM_CATEGORY.name]
        nodes = frames[DIM_INDICATOR_NODE.name]
        results.extend(
            [
                foreign_key("fk.observation.geography", obs, "geography_key", geo, "geography_key"),
                foreign_key(
                    "fk.observation.breakdown",
                    obs,
                    "breakdown_key",
                    frames[DIM_BREAKDOWN.name],
                    "breakdown_key",
                ),
                foreign_key(
                    "fk.observation.period", obs, "period", frames[DIM_PERIOD.name], "period"
                ),
                foreign_key(
                    "fk.observation.indicator",
                    obs,
                    "indicator_id",
                    frames[DIM_INDICATOR.name],
                    "indicator_id",
                ),
                foreign_key(
                    "fk.breakdown.category",
                    frames[DIM_BREAKDOWN.name],
                    "category_keys",
                    cats,
                    "category_key",
                ),
                foreign_key(
                    "fk.indicator.node", frames[DIM_INDICATOR.name], "node_key", nodes, "node_key"
                ),
                foreign_key("fk.node.parent", nodes, "parent_key", nodes, "node_key"),
                foreign_key("fk.geography.parent", geo, "parent_key", geo, "geography_key"),
            ]
        )
        if DIM_GEOMETRY.name in frames:
            results.append(
                foreign_key(
                    "fk.geometry.geography",
                    frames[DIM_GEOMETRY.name],
                    "geography_key",
                    geo,
                    "geography_key",
                )
            )
        for fact in self._catalog.facts:
            for column in fact.classifications.values():
                results.append(
                    foreign_key(
                        f"fk.{fact.id}.{column}", frames[fact.id], column, cats, "category_key"
                    )
                )
        results.extend(geography_checks(geo, frames[BRIDGE_GEOGRAPHY_ANCESTOR.name]))
        results.append(silver_fidelity(selected, obs))
        results.extend(category_reconciliation(obs, self._catalog))
        results.extend(consistency_checks(obs, self._catalog))
        return results

    def _write(self, build: GoldBuild, frames: Mapping[str, pl.DataFrame]) -> None:
        contracts = self.contracts()
        evolve: dict[str, bool] = {}
        # Todos os schemas são conferidos antes da primeira escrita.
        for name in frames:
            uri = self.table_uri(name)
            evolve[name] = False
            if DeltaTable.is_deltatable(uri):
                existing = pl.scan_delta(uri).collect_schema()
                comparison = compare_schema(existing, contracts[name])
                if comparison.change is SchemaChange.INCOMPATIBLE:
                    msg = f"{name}: mudança de schema incompatível: {list(comparison.details)}"
                    raise GoldBuildError(msg)
                evolve[name] = comparison.change is SchemaChange.COMPATIBLE_ADDITION
        for name, frame in frames.items():
            contract = contracts[name]
            result = self._writer.write(
                self.table_uri(name),
                frame,
                run_id=build.build_id,
                mode="overwrite",
                partition_by=list(contract.partition_by),
                evolve_schema=evolve[name],
            )
            build.tables[name] = GoldTable(
                table_id=name,
                storage_uri=result.table_uri,
                delta_version=result.version,
                contract_version=contract.version,
                rows=frame.height,
            )
