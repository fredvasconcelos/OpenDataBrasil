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
    BatchedTableChecks,
    category_reconciliation,
    consistency_checks,
    fidelity_diff,
    fidelity_result,
    foreign_key,
    geography_checks,
    geometry_checks,
    input_checks,
    table_checks,
)
from odb_processing.contracts import SIDRA_OBSERVATION, Contract, SchemaChange, compare_schema
from odb_processing.quality import CheckResult, blocking
from odb_processing.silver import PreviousRun
from odb_semantics import SemanticCatalog

logger = logging.getLogger(__name__)

# Categoria Total das Silvers marginais (Sinesp VDE e SIM).
MARGINAL_TOTAL = "T"

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
            transformer = dataset.silver.get("transformer")
            if transformer == "datasus_sim_do":
                # SIM: óbitos por residência, um arquivo por UF e ano numa tabela Silver.
                out[dataset_id] = model.DatasetInfo(
                    dataset_id=dataset_id,
                    table_id=str(dataset.silver.get("table_id", "SIM-DORES")),
                    reference_url=dataset.reference_url,
                    license_id=dataset.license,
                    period_type="ano",
                    marginals=True,
                )
                continue
            if transformer != "sidra_observation":
                msg = f"{dataset_id}: a Gold desta versão aceita SIDRA, Sinesp VDE e SIM"
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
            marginals=True,
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
                # Lotes já gravados ficam em versões Delta sem release: não servem a nada.
                build.tables = {}
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
        self._build_in_batches(build)
        failures = blocking(build.checks)
        if failures:
            msg = "verificações bloqueantes falharam: " + ", ".join(c.check_id for c in failures)
            raise GoldBuildError(msg)
        build.status = "succeeded"

    def _build_in_batches(self, build: GoldBuild) -> None:
        """Constrói e grava a Gold um dataset por vez (KI-007, etapa 2; §8.2, §8.4).

        Cada lote lê da Silver só as tabelas e variáveis de um dataset, monta as
        observações e os fatos dele, grava e libera a memória. Do lote ficam só
        resumos pequenos (períodos, territórios, categorias, chaves), com que as
        dimensões e as verificações finais são montadas.

        As tabelas são gravadas durante o build, mas escrita não é publicação
        (§10.9): o release só é criado se todas as verificações passarem, e a
        consulta continua nas versões Delta fixadas no release ativo.
        """
        inputs = build.inputs
        datasets = self.datasets()
        mapping = model.indicator_map(self._catalog, datasets)
        contracts = self.contracts()
        evolve = self._schema_plan(contracts)
        scan = self._silver_scan(inputs, datasets)
        names = model.municipal_names(scan)
        pending, pending_report = model.resolve_pending_installation(self._catalog, names, datasets)
        versions = self._silver_versions(inputs, datasets)
        period_types = {d.dataset_id: d.period_type for d in datasets.values()}
        consistency_ids = {
            i for pair in self._catalog.consistency for i in (pair.indicator, pair.reference)
        }
        summary = _Summary()
        observations_out = _BatchedTable(self, build, contracts[INDICATOR_OBSERVATION.name], evolve)
        table_results: list[CheckResult] = []
        for dataset_id in sorted(datasets):
            info = datasets[dataset_id]
            part = mapping.filter(pl.col("dataset_id") == dataset_id)
            silver = (
                scan.filter(pl.col("table_id").is_in(list(info.source_tables)))
                .join(
                    part.lazy().select("table_id", "variable_id").unique(),
                    on=["table_id", "variable_id"],
                    how="semi",
                )
                .collect(engine="streaming")
            )
            selected, fixed_problems = model.strip_fixed_categories(
                model.select_silver(silver, part, self._catalog), self._catalog
            )
            del silver
            observations = model.build_observations(
                selected,
                self._catalog,
                silver_version=versions,
                build_id=build.build_id,
                pending=pending,
                period_types=period_types,
            )
            summary.add(selected, observations, fixed_problems)
            indicators = set(part["indicator_id"].to_list())
            summary.reconciliation.extend(
                category_reconciliation(observations, self._catalog, indicators)
            )
            if consistency_ids & indicators:
                summary.consistency.append(
                    observations.filter(pl.col("indicator_id").is_in(list(consistency_ids)))
                )
            for fact in self._catalog.facts:
                if fact.dataset != dataset_id:
                    continue
                frame = model.build_fact(observations, self._catalog, fact, contracts[fact.id])
                table_results.extend(table_checks(fact.id, frame, contracts[fact.id]))
                summary.add_fact_categories(fact.id, frame, fact.classifications.values())
                self._write_table(build, fact.id, frame, contracts[fact.id], evolve)
            observations_out.add(observations)
            logger.info(
                "gold batch written",
                extra={"dataset_id": dataset_id, "observations": observations.height},
            )
            del selected, observations
        observations_out.close()
        summary.municipal_names = names
        summary.pending_report = pending_report
        entry, rest = self._finish(build, summary, datasets, contracts, evolve)
        build.checks = [*entry, *observations_out.checks.results(), *table_results, *rest]

    def _finish(
        self,
        build: GoldBuild,
        summary: _Summary,
        datasets: Mapping[str, model.DatasetInfo],
        contracts: Mapping[str, Contract],
        evolve: Mapping[str, bool],
    ) -> tuple[list[CheckResult], list[CheckResult]]:
        """Dimensões a partir dos resumos, verificações de conjunto e gravação das dimensões.

        Devolve as verificações de entrada (catálogo contra a Silver) e as demais.
        """
        inputs = build.inputs
        selected = summary.selected()
        observed = summary.observed()
        ref = inputs["reference"]
        dtb_all = self._reader.scan(ref["uri"], int(ref["delta_version"])).collect()
        year = str(dtb_all["reference_year"].max())
        dtb = dtb_all.filter(pl.col("reference_year") == year)
        try:
            geography = build_dim_geography(
                dtb,
                observed,
                reference=f"{ref['dataset_id']} {year} (Silver v{ref['delta_version']})",
                uf_abbreviations=model.uf_abbreviations(summary.municipal_names),
            )
            bridge = build_ancestor_bridge(geography)
        except GeographyError as exc:
            raise GoldBuildError(str(exc)) from exc

        used = sorted({cid for f in self._catalog.facts for cid in f.classifications})
        categories = model.build_dim_category(
            self._catalog, used, model.category_names(summary.categories(), self._catalog)
        )
        keys = summary.keys()
        frames: dict[str, pl.DataFrame] = {}
        geometry_results: list[CheckResult] = []
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
            frames[DIM_GEOMETRY.name] = geometry
            geometry_results = geometry_checks(geometry, report)
        frames |= {
            DIM_GEOGRAPHY.name: geography,
            BRIDGE_GEOGRAPHY_ANCESTOR.name: bridge,
            DIM_PERIOD.name: model.build_dim_period(keys["period"]),
            DIM_CLASSIFICATION.name: model.build_dim_classification(self._catalog, used),
            DIM_CATEGORY.name: categories,
            DIM_BREAKDOWN.name: model.build_dim_breakdown(
                keys["breakdown_key"], categories, self._catalog
            ),
            DIM_INDICATOR.name: model.build_dim_indicator(
                self._catalog,
                summary.stats(),
                summary.variable_names(),
                datasets,
                model.indicator_node_keys(self._catalog),
            ),
            DIM_INDICATOR_NODE.name: model.build_dim_indicator_node(
                self._catalog, summary.indicator_breakdowns(), categories
            ),
        }
        entry = input_checks(
            selected, self._catalog, datasets, summary.pending_report, summary.fixed_problems
        )
        results: list[CheckResult] = []
        for name, frame in frames.items():
            results.extend(table_checks(name, frame, contracts[name]))
        results.extend(self._key_checks(frames, keys, summary))
        results.extend(geography_checks(geography, bridge))
        results.append(fidelity_result(summary.fidelity, summary.rows))
        results.extend(summary.reconciliation)
        results.extend(consistency_checks(summary.consistency_frame(), self._catalog))
        results.extend(geometry_results)
        for name, frame in frames.items():
            self._write_table(build, name, frame, contracts[name], evolve)
        return entry, results

    def _key_checks(
        self,
        frames: Mapping[str, pl.DataFrame],
        keys: Mapping[str, pl.DataFrame],
        summary: _Summary,
    ) -> list[CheckResult]:
        """Integridade referencial, com as chaves das observações resumidas por lote."""
        geo = frames[DIM_GEOGRAPHY.name]
        cats = frames[DIM_CATEGORY.name]
        nodes = frames[DIM_INDICATOR_NODE.name]
        breakdown = frames[DIM_BREAKDOWN.name]
        results = [
            foreign_key(
                "fk.observation.geography",
                keys["geography_key"],
                "geography_key",
                geo,
                "geography_key",
            ),
            foreign_key(
                "fk.observation.breakdown",
                keys["breakdown_key"],
                "breakdown_key",
                breakdown,
                "breakdown_key",
            ),
            foreign_key(
                "fk.observation.period", keys["period"], "period", frames[DIM_PERIOD.name], "period"
            ),
            foreign_key(
                "fk.observation.indicator",
                keys["indicator_id"],
                "indicator_id",
                frames[DIM_INDICATOR.name],
                "indicator_id",
            ),
            foreign_key("fk.breakdown.category", breakdown, "category_keys", cats, "category_key"),
            foreign_key(
                "fk.indicator.node", frames[DIM_INDICATOR.name], "node_key", nodes, "node_key"
            ),
            foreign_key("fk.node.parent", nodes, "parent_key", nodes, "node_key"),
            foreign_key("fk.geography.parent", geo, "parent_key", geo, "geography_key"),
        ]
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
                values = summary.fact_categories.get((fact.id, column))
                child = (
                    values
                    if values is not None
                    else pl.DataFrame({column: []}, schema={column: pl.String})
                )
                results.append(
                    foreign_key(f"fk.{fact.id}.{column}", child, column, cats, "category_key")
                )
        return results

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
        keep = self._marginal_filter(datasets)
        return scan if keep is None else scan.filter(keep)

    def _marginal_filter(self, datasets: Mapping[str, model.DatasetInfo]) -> pl.Expr | None:
        """Linhas das Silvers marginais (Sinesp VDE, SIM) que algum fato usa.

        Nelas cada linha traz o Total ou a distribuição de uma dimensão, com as demais no
        Total (``T``). Um fato usa a linha quando cada dimensão está na categoria fixa do
        fato, no Total, ou é uma classificação do fato. Sem isso, o build carregaria todas
        as distribuições (o Sinesp tem ~34 milhões de linhas) para usar só o Total.
        """
        tables: list[str] = []
        used: pl.Expr = pl.lit(value=False)
        for info in datasets.values():
            if not info.marginals:
                continue
            tables.extend(info.source_tables)
            for fact in self._catalog.facts:
                if fact.dataset != info.dataset_id:
                    continue
                dim = pl.element().struct.field("dimension")
                expected = (
                    dim.replace_strict(dict(fact.fixed_categories), default=pl.lit(MARGINAL_TOTAL))
                    if fact.fixed_categories
                    else pl.lit(MARGINAL_TOTAL)
                )
                allowed = pl.element().struct.field("category_id") == expected
                classified = [
                    self._catalog.classification(c).silver_dimension for c in fact.classifications
                ]
                if classified:
                    allowed = allowed | dim.is_in(classified)
                used = used | (
                    pl.col("table_id").is_in(list(info.source_tables))
                    & pl.col("classifications").list.eval(allowed).list.all()
                )
        if not tables:
            return None
        return ~pl.col("table_id").is_in(tables) | used

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

    def _schema_plan(self, contracts: Mapping[str, Contract]) -> dict[str, bool]:
        """Confere o schema de todas as tabelas antes da primeira escrita.

        Devolve, por tabela, se a escrita deve acrescentar colunas (evolução compatível).
        """
        evolve: dict[str, bool] = {}
        for name, contract in contracts.items():
            uri = self.table_uri(name)
            evolve[name] = False
            if DeltaTable.is_deltatable(uri):
                existing = pl.scan_delta(uri).collect_schema()
                comparison = compare_schema(existing, contract)
                if comparison.change is SchemaChange.INCOMPATIBLE:
                    msg = f"{name}: mudança de schema incompatível: {list(comparison.details)}"
                    raise GoldBuildError(msg)
                evolve[name] = comparison.change is SchemaChange.COMPATIBLE_ADDITION
        return evolve

    def _write_table(
        self,
        build: GoldBuild,
        name: str,
        frame: pl.DataFrame,
        contract: Contract,
        evolve: Mapping[str, bool],
        *,
        mode: Literal["overwrite", "append"] = "overwrite",
        rows: int | None = None,
    ) -> None:
        """Grava uma tabela (ou um lote dela) e registra a versão Delta resultante."""
        result = self._writer.write(
            self.table_uri(name),
            frame,
            run_id=build.build_id,
            mode=mode,
            partition_by=list(contract.partition_by),
            evolve_schema=evolve[name],
        )
        build.tables[name] = GoldTable(
            table_id=name,
            storage_uri=result.table_uri,
            delta_version=result.version,
            contract_version=contract.version,
            rows=frame.height if rows is None else rows,
        )


# Linhas de observação acumuladas antes de cada gravação: poucos arquivos por partição
# sem guardar a tabela inteira na memória (cerca de 0,5 GB por lote gravado).
OBSERVATION_FLUSH_ROWS = 2_000_000


class _BatchedTable:
    """``indicator_observation`` gravada em lotes: o primeiro substitui a tabela."""

    def __init__(
        self,
        builder: GoldBuilder,
        build: GoldBuild,
        contract: Contract,
        evolve: Mapping[str, bool],
    ) -> None:
        self._builder = builder
        self._build = build
        self._contract = contract
        self._evolve = evolve
        self._buffer: list[pl.DataFrame] = []
        self._buffered = 0
        self._written = 0
        self._writes = 0
        self.checks = BatchedTableChecks(contract.name, contract)

    def add(self, frame: pl.DataFrame) -> None:
        """Confere o lote e grava quando o acúmulo passa do limite."""
        self.checks.add(frame)
        self._buffer.append(frame)
        self._buffered += frame.height
        if self._buffered >= OBSERVATION_FLUSH_ROWS:
            self._flush()

    def close(self) -> None:
        """Grava o restante (ou a tabela vazia, se nada foi gravado)."""
        if self._buffer or not self._writes:
            self._flush()

    def _flush(self) -> None:
        frame = (
            pl.concat(self._buffer)
            if self._buffer
            else pl.DataFrame(schema=self._contract.frame_schema())
        )
        self._written += frame.height
        self._builder._write_table(
            self._build,
            self._contract.name,
            frame,
            self._contract,
            self._evolve,
            mode="append" if self._writes else "overwrite",
            rows=self._written,
        )
        self._writes += 1
        self._buffer, self._buffered = [], 0


# Colunas da Silver que as verificações de entrada usam (``input_checks``): o resumo
# de cada lote guarda só as combinações distintas delas, sem território nem período.
_INPUT_KEYS = (
    "table_id",
    "variable_id",
    "unit_name",
    "value_status",
    "territorial_level",
    "indicator_id",
    "fact_table",
    "classification_key",
)
_OBSERVATION_KEYS = ("geography_key", "breakdown_key", "period", "indicator_id")


class _Summary:
    """O que cada lote deixa para as dimensões e as verificações finais (KI-007)."""

    def __init__(self) -> None:
        self._selected: list[pl.DataFrame] = []
        self._categories: list[pl.DataFrame] = []
        self._observed: list[pl.DataFrame] = []
        self._names: list[pl.DataFrame] = []
        self._stats: list[pl.DataFrame] = []
        self._breakdowns: list[pl.DataFrame] = []
        self._keys: dict[str, list[pl.DataFrame]] = {k: [] for k in _OBSERVATION_KEYS}
        self.fixed_problems: dict[str, dict[str, list[str]]] = {}
        self.fidelity: dict[str, Any] = {}
        self.rows = 0
        self.reconciliation: list[CheckResult] = []
        self.consistency: list[pl.DataFrame] = []
        self.fact_categories: dict[tuple[str, str], pl.DataFrame] = {}
        # Preenchidos pelo build depois dos lotes.
        self.municipal_names = pl.DataFrame()
        self.pending_report: Sequence[Mapping[str, object]] = ()

    def add(
        self,
        selected: pl.DataFrame,
        observations: pl.DataFrame,
        fixed_problems: Mapping[str, Mapping[str, list[str]]],
    ) -> None:
        """Resumo de um lote."""
        self._selected.append(
            selected.unique(list(_INPUT_KEYS)).select(*_INPUT_KEYS, "classifications")
        )
        self._categories.append(
            selected.select("period", "classification_key", "classifications").unique(
                ["period", "classification_key"]
            )
        )
        self._observed.append(
            selected.sort("period", descending=True)
            .select(
                "period",
                pl.col("territorial_level")
                .replace_strict(model.SIDRA_LEVELS, default=None)
                .alias("level_id"),
                pl.col("territory_id").alias("code"),
                pl.col("territory_name").alias("name"),
            )
            .unique(["level_id", "code"], keep="first")
        )
        self._names.append(
            selected.sort("period", descending=True)
            .unique("indicator_id", keep="first")
            .select("indicator_id", "period", "variable_name")
        )
        self._stats.append(model.indicator_stats(observations))
        self._breakdowns.append(observations.select("indicator_id", "breakdown_key").unique())
        for key in _OBSERVATION_KEYS:
            self._keys[key].append(observations.select(key).unique())
        for fact_id, dims in fixed_problems.items():
            self.fixed_problems.setdefault(fact_id, {}).update(dims)
        self.fidelity.update(fidelity_diff(selected, observations))
        self.rows += observations.height

    def add_fact_categories(self, fact_id: str, frame: pl.DataFrame, columns: Any) -> None:
        """Categorias usadas por um fato (para a integridade com ``dim_category``)."""
        for column in columns:
            self.fact_categories[(fact_id, column)] = frame.select(column).unique()

    def selected(self) -> pl.DataFrame:
        """Combinações distintas da Silver selecionada, para ``input_checks``."""
        return pl.concat(self._selected) if self._selected else pl.DataFrame()

    def categories(self) -> pl.DataFrame:
        """Categorias observadas por período, para ``category_names``."""
        return pl.concat(self._categories)

    def observed(self) -> pl.DataFrame:
        """Territórios observados, com o nome do período mais recente."""
        return (
            pl.concat(self._observed)
            .sort("period", descending=True)
            .unique(["level_id", "code"], keep="first")
            .drop("period")
        )

    def variable_names(self) -> pl.DataFrame:
        """Nome publicado da variável de cada indicador (período mais recente)."""
        return pl.concat(self._names)

    def stats(self) -> pl.DataFrame:
        """Níveis, períodos e contagem por indicador."""
        return pl.concat(self._stats)

    def indicator_breakdowns(self) -> pl.DataFrame:
        """Pares indicador e desagregação observados."""
        return pl.concat(self._breakdowns)

    def keys(self) -> dict[str, pl.DataFrame]:
        """Valores distintos das chaves das observações."""
        return {k: pl.concat(v).unique() for k, v in self._keys.items()}

    def consistency_frame(self) -> pl.DataFrame:
        """Observações dos indicadores comparados em ``[[consistency]]``."""
        if not self.consistency:
            return pl.DataFrame(schema=INDICATOR_OBSERVATION.frame_schema())
        return pl.concat(self.consistency)
