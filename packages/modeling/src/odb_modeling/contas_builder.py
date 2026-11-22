"""Construção da Gold do escopo ``contas`` (ADR-0036).

Mesmo ciclo do ``GoldBuilder`` (impressão digital, ``skipped``, verificações bloqueantes,
escrita sem publicação, release por manifesto), com outro modelo: fatos de entidade,
dimensões com chave inteira e agregados por território (ADR-0034).

Fluxo:

1. resolve as Silvers vigentes das lentes A, B e C, do cadastro PJ e da DTB, e calcula a
   impressão digital. Sem mudança, termina ``skipped``;
2. monta as dimensões sobre todos os meses (leitura em streaming, só as colunas usadas);
3. para cada ano, monta os fatos de cada lente, os agregados por território e o ranking,
   confere e grava (o primeiro lote substitui a tabela, os seguintes acrescentam);
4. confere as lentes A x C por mês e ação e calcula a situação de cada mês;

Antes do passo 2, o FPM da lente A é conferido com o do Tesouro por município e mês, e o
complemento dos meses abaixo do Tesouro entra na lente A como linhas marcadas (ADR-0038).
5. grava as dimensões e roda as verificações de conjunto. Uma falha bloqueante deixa a
   construção ``failed``: as versões gravadas não entram em nenhum release.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import polars as pl
from deltalake import DeltaTable

from odb_common.logging import log_context
from odb_common.storage import LakehouseLayout, Layer
from odb_ingestion.config import SourceCatalog
from odb_lakehouse import DeltaReader, DeltaWriter
from odb_modeling import contas, model
from odb_modeling.builder import GoldBuild, GoldBuildError, GoldRegistry, GoldTable
from odb_modeling.contas_contracts import (
    AGG_CONTAS_PERIOD_STATUS,
    AGG_CONTAS_TERRITORY,
    AGG_FPM_RECONCILIATION,
    AGG_RECIPIENT_RANK,
    AGG_TRANSFER_RECONCILIATION,
    CONTAS_CONTRACTS,
    DIM_RECIPIENT,
    FACT_FEDERAL_BUDGET_EXECUTION,
    FACT_FEDERAL_PAYMENT_RECIPIENT,
    FACT_FEDERAL_TRANSFER,
)
from odb_modeling.contracts import (
    BRIDGE_GEOGRAPHY_ANCESTOR,
    BRIDGE_PERIOD_ANCESTOR,
    DIM_GEOGRAPHY,
    DIM_PERIOD,
)
from odb_modeling.geography import GeographyError, build_ancestor_bridge, build_dim_geography
from odb_modeling.quality import BatchedTableChecks, foreign_key, geography_checks, table_checks
from odb_processing.contracts import Contract, SchemaChange, compare_schema
from odb_processing.quality import CheckResult, CheckStatus, blocking
from odb_processing.silver import PreviousRun
from odb_processing.values import VALUE_DTYPE

logger = logging.getLogger(__name__)

CONTAS_SCOPE = "contas"
# Sobe quando a modelagem muda sem mudar contratos, para forçar a reconstrução.
CONTAS_MODEL_VERSION = "1.0.0"
# Ranking: 100 páginas de 10 linhas (ADR-0034, decisão 3).
TOP_N = 1000

# Papel → transformer Silver (o id do dataset vem da configuração das fontes).
ROLES: Mapping[str, str] = {
    "transfers": "cgu_transfer",
    "payments": "cgu_recipient_payment",
    "execution": "cgu_budget_execution",
    "legal_entities": "cgu_legal_entity",
    # Segunda fonte do FPM da lente A (ADR-0038).
    "fpm_treasury": "tesouro_fpm_municipality",
}

_TRANSFER_COLUMNS = (
    "period", "uf", "municipality_id", "territory_status", "transfer_type", "recipient_type",
    "recipient_code", "recipient_name", "recipient_class", "legal_nature_code", "organ_code",
    "organ_name", "management_unit_code", "management_unit_name", "function_code",
    "function_name", "subfunction_code", "subfunction_name", "program_code", "program_name",
    "action_code", "action_name", "citizen_language", "expense_group_code",
    "expense_group_name", "application_modality_code", "application_modality_name",
    "expense_element_code", "expense_element_name", "value",
)  # fmt: skip
_PAYMENT_COLUMNS = (
    "period", "uf", "municipality_id", "territory_status", "recipient_code", "recipient_name",
    "recipient_class", "legal_nature_code", "superior_organ_code", "superior_organ_name",
    "organ_code", "organ_name", "management_unit_code", "management_unit_name", "value",
)  # fmt: skip
_EXECUTION_COLUMNS = (
    "period", "superior_organ_code", "superior_organ_name", "organ_code", "organ_name",
    "management_unit_code", "management_unit_name", "function_code", "function_name",
    "subfunction_code", "subfunction_name", "program_code", "program_name", "action_code",
    "action_name", "amendment_author_code", "amendment_author_name", "economic_category_code",
    "economic_category_name", "expense_group_code", "expense_group_name",
    "application_modality_code", "application_modality_name", "expense_element_code",
    "expense_element_name", *contas.EXECUTION_MEASURES,
)  # fmt: skip


def _detached(frame: pl.DataFrame) -> pl.DataFrame:
    """Cópia sem referência aos buffers do lote (ver ``builder._detached``)."""
    return pl.from_arrow(frame.to_arrow(compat_level=pl.CompatLevel.oldest()))  # type: ignore[return-value]


@dataclass
class _Table:
    """Tabela gravada em lotes disjuntos na chave: o primeiro substitui, os demais somam."""

    contract: Contract
    checks: BatchedTableChecks
    writes: int = 0
    rows: int = 0
    geography: list[pl.DataFrame] = field(default_factory=list)


_BATCHED = (
    FACT_FEDERAL_TRANSFER,
    FACT_FEDERAL_PAYMENT_RECIPIENT,
    FACT_FEDERAL_BUDGET_EXECUTION,
    AGG_CONTAS_TERRITORY,
    AGG_RECIPIENT_RANK,
)


@dataclass
class _Run:
    """Estado de uma construção: tabelas em lotes e resumos pequenos de cada lote."""

    build: GoldBuild
    dims: contas.Dimensions
    evolve: Mapping[str, bool]
    batched: dict[str, _Table] = field(
        default_factory=lambda: {c.name: _Table(c, BatchedTableChecks(c.name, c)) for c in _BATCHED}
    )
    fidelity: list[pl.DataFrame] = field(default_factory=list)
    partition: list[pl.DataFrame] = field(default_factory=list)
    totals: dict[str, list[pl.DataFrame]] = field(
        default_factory=lambda: {"A": [], "B": [], "C": []}
    )
    by_action: dict[str, list[pl.DataFrame]] = field(default_factory=lambda: {"A": [], "C": []})


class ContasGoldBuilder:
    """Constrói a Gold das contas públicas a partir das Silvers vigentes."""

    scope = CONTAS_SCOPE

    def __init__(
        self,
        sources: SourceCatalog,
        layout: LakehouseLayout,
        writer: DeltaWriter,
        registry: GoldRegistry,
        *,
        code_version: str = "unknown",
        top_n: int = TOP_N,
    ) -> None:
        """Recebe as fontes, o lakehouse, o escritor e o registro."""
        self._sources = sources
        self._layout = layout
        self._writer = writer
        self._registry = registry
        self._code_version = code_version
        self._top_n = top_n
        self._reader = DeltaReader()
        self._reset_schema: frozenset[str] = frozenset()

    # ------------------------------------------------------------- configuração

    def table_uri(self, table_id: str) -> str:
        """URI de uma tabela Gold do escopo."""
        return self._layout.table_uri(Layer.GOLD, self.scope, table_id)

    def contracts(self) -> dict[str, Contract]:
        """Contratos de todas as tabelas do escopo."""
        shared = (DIM_GEOGRAPHY, BRIDGE_GEOGRAPHY_ANCESTOR, DIM_PERIOD, BRIDGE_PERIOD_ANCESTOR)
        return {c.name: c for c in (*shared, *CONTAS_CONTRACTS)}

    def datasets(self) -> dict[str, str]:
        """Papel → dataset, pelo transformer Silver declarado nas fontes."""
        out: dict[str, str] = {}
        for role, transformer in ROLES.items():
            found = [
                d.id
                for d in self._sources.datasets.values()
                if d.silver.get("transformer") == transformer
            ]
            if len(found) != 1:
                msg = f"contas: esperado um dataset com transformer {transformer}, há {found}"
                raise GoldBuildError(msg)
            out[role] = found[0]
        return out

    def reference_dataset(self, datasets: Mapping[str, str]) -> str:
        """DTB das lentes com território (a mesma nas duas)."""
        refs = {
            str(self._sources.dataset(datasets[r]).silver.get("territorial_reference"))
            for r in ("transfers", "payments")
        }
        if len(refs) != 1 or "None" in refs:
            msg = f"contas: as lentes A e B precisam da mesma referência territorial: {refs}"
            raise GoldBuildError(msg)
        return refs.pop()

    # ------------------------------------------------------------- execução

    def build(
        self,
        *,
        pipeline_run_id: str | None = None,
        force: bool = False,
        reset_schema: Sequence[str] = (),
    ) -> GoldBuild:
        """Constrói a Gold. Erros ficam registrados no ``GoldBuild``."""
        self._reset_schema = frozenset(reset_schema)
        build = GoldBuild(
            build_id=str(uuid.uuid4()),
            scope=self.scope,
            config_version=f"contas-model@{CONTAS_MODEL_VERSION}",
            code_version=self._code_version,
        )
        with log_context(gold_build_id=build.build_id, scope=build.scope):
            try:
                build.inputs = self._resolve_inputs()
                build.input_fingerprint = self._fingerprint(build.inputs)
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
                build.tables = {}
                logger.exception("contas gold build failed")
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
        datasets = self.datasets()
        roles = {**datasets, "reference": self.reference_dataset(datasets)}
        out: dict[str, Any] = {}
        for role, dataset_id in sorted(roles.items()):
            run = self._silver(dataset_id)
            out[role] = {
                "dataset_id": dataset_id,
                "run_id": run.run_id,
                "uri": run.target_uri,
                "delta_version": run.delta_version,
            }
        return out

    def _fingerprint(self, inputs: Mapping[str, Any]) -> str:
        payload = {
            "model_version": CONTAS_MODEL_VERSION,
            "contracts": {n: c.version for n, c in sorted(self.contracts().items())},
            "parameters": {
                "top_n": self._top_n,
                "incomplete_share": contas.INCOMPLETE_SHARE,
                "action_tolerance": [
                    contas.ACTION_TOLERANCE_SHARE,
                    contas.ACTION_TOLERANCE_VALUE,
                ],
                "transfer_modalities": list(contas.TRANSFER_MODALITIES),
                "not_ranked": list(contas.NOT_RANKED),
                "fpm_action": contas.FPM_ACTION,
                "fpm_cent": contas.FPM_CENT,
            },
            "inputs": inputs,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _unchanged(self, build: GoldBuild) -> bool:
        previous = self._registry.last_success(build.scope)
        if previous is None or previous.input_fingerprint != build.input_fingerprint:
            return False
        if set(previous.tables) != set(self.contracts()):
            return False
        if all(
            self._reader.has_version(t.storage_uri, t.delta_version)
            for t in previous.tables.values()
        ):
            build.tables = dict(previous.tables)
            return True
        return False

    def _scan(self, inputs: Mapping[str, Any], role: str, columns: Sequence[str]) -> pl.LazyFrame:
        info = inputs[role]
        return self._reader.scan(str(info["uri"]), int(info["delta_version"])).select(columns)

    def _execute(self, build: GoldBuild, *, force: bool) -> None:
        if not force and self._unchanged(build):
            build.status = "skipped"
            logger.info("contas gold unchanged")
            return
        contracts = self.contracts()
        evolve = self._schema_plan(contracts)
        inputs = build.inputs
        transfers = self._scan(inputs, "transfers", _TRANSFER_COLUMNS)
        treasury = self._scan(inputs, "fpm_treasury", ("period", "municipality_id", "value"))
        fpm = contas.fpm_complement(transfers, treasury)
        logger.info(
            "contas fpm complement",
            extra={"rows": fpm.rows.height, "months": fpm.rows["period"].n_unique()},
        )
        transfers = pl.concat(
            [
                transfers.with_columns(pl.lit(contas.SOURCE_CGU).alias("value_source")),
                fpm.rows.lazy(),
            ]
        )
        payments = self._scan(inputs, "payments", _PAYMENT_COLUMNS)
        execution = self._scan(inputs, "execution", _EXECUTION_COLUMNS)
        legal = self._legal_entities(inputs)
        recipients = contas.build_dim_recipient(transfers, payments, legal)
        del legal
        dims = contas.Dimensions(
            recipient=recipients.frame,
            management_unit=contas.build_dim_management_unit([transfers, payments, execution]),
            budget_action=contas.build_dim_budget_action([transfers, execution]),
            expense_nature=contas.build_dim_expense_nature([transfers, execution], execution),
            amendment_author=contas.build_dim_amendment_author(execution),
        )
        logger.info("contas dimensions", extra={k: v.height for k, v in dims.frames().items()})
        run = _Run(build, dims, evolve)
        for year in self._years([transfers, payments, execution]):
            in_year = pl.col("period").str.starts_with(year)
            self._transfers_year(run, transfers.filter(in_year))
            self._payments_year(run, payments.filter(in_year))
            self._execution_year(run, execution.filter(in_year))
            logger.info("contas gold year written", extra={"year": year})
        batched, totals, by_action = run.batched, run.totals, run.by_action
        checks: list[CheckResult] = []

        reconciliation = contas.transfer_reconciliation(
            pl.concat(by_action["A"]), pl.concat(by_action["C"])
        )
        status = contas.period_status(
            {lens: pl.concat(parts) for lens, parts in totals.items()},
            reconciliation,
            complements=_complements(fpm.rows),
        )
        periods = pl.concat([pl.concat(p).select("period") for p in totals.values()]).unique()
        geography, bridge = self._geography(inputs)
        small = {
            **dims.frames(),
            AGG_TRANSFER_RECONCILIATION.name: reconciliation,
            AGG_FPM_RECONCILIATION.name: fpm.reconciliation,
            AGG_CONTAS_PERIOD_STATUS.name: status,
            DIM_GEOGRAPHY.name: geography,
            BRIDGE_GEOGRAPHY_ANCESTOR.name: bridge,
            DIM_PERIOD.name: model.build_dim_period(periods),
            BRIDGE_PERIOD_ANCESTOR.name: model.build_bridge_period_ancestor(periods),
        }
        for name, frame in small.items():
            checks.extend(table_checks(name, frame, contracts[name]))
        for table in batched.values():
            checks.extend(table.checks.results())
        checks.extend(geography_checks(geography, bridge))
        checks.extend(self._set_checks(small, batched, recipients.class_conflicts))
        checks.append(_fidelity_result(pl.concat(run.fidelity)))
        checks.append(_partition_result(pl.concat(run.partition)))
        checks.extend(_reconciliation_results(status))
        checks.extend(_fpm_results(fpm))
        build.checks = checks
        failures = blocking(checks)
        if failures:
            msg = "verificações bloqueantes falharam: " + ", ".join(c.check_id for c in failures)
            raise GoldBuildError(msg)
        for name, frame in small.items():
            self._write(build, name, frame, contracts[name], evolve, mode="overwrite")
        build.status = "succeeded"

    # ------------------------------------------------------------- lotes anuais

    def _transfers_year(self, run: _Run, silver: pl.LazyFrame) -> None:
        """Lente A de um ano: fato, agregados por território e ranking."""
        fact = contas.transfer_fact(silver, run.dims)
        run.fidelity.append(_fidelity("A", silver, fact, ["value"]))
        run.totals["A"].append(_totals(fact, "value"))
        run.by_action["A"].append(_detached(contas.transfers_by_action(silver)))
        self._add(run, FACT_FEDERAL_TRANSFER.name, fact)
        self._aggregates(run, fact, contas.LENS_TRANSFERS)

    def _payments_year(self, run: _Run, silver: pl.LazyFrame) -> None:
        """Lente B de um ano: fato, agregados por território e ranking."""
        fact = contas.payment_fact(silver, run.dims)
        run.fidelity.append(_fidelity("B", silver, fact, ["value"]))
        run.totals["B"].append(_totals(fact, "value"))
        self._add(run, FACT_FEDERAL_PAYMENT_RECIPIENT.name, fact)
        self._aggregates(run, fact, contas.LENS_PAYMENTS)

    def _execution_year(self, run: _Run, silver: pl.LazyFrame) -> None:
        """Lente C de um ano: só o fato (sem território, ADR-0032, decisão 6)."""
        fact = contas.execution_fact(silver, run.dims)
        run.fidelity.append(_fidelity("C", silver, fact, list(contas.EXECUTION_MEASURES)))
        run.totals["C"].append(_totals(fact, "paid"))
        run.by_action["C"].append(_detached(contas.execution_by_action(silver)))
        self._add(run, FACT_FEDERAL_BUDGET_EXECUTION.name, fact)

    def _aggregates(self, run: _Run, fact: pl.DataFrame, lens: str) -> None:
        agg = contas.territory_aggregates(contas.with_attributes(fact, run.dims, lens), lens)
        run.partition.append(_partition_check(agg))
        self._add(run, AGG_CONTAS_TERRITORY.name, agg)
        del agg
        self._add(run, AGG_RECIPIENT_RANK.name, contas.recipient_rank(fact, lens, self._top_n))

    # ------------------------------------------------------------- partes

    def _years(self, scans: Sequence[pl.LazyFrame]) -> list[str]:
        periods = pl.concat([s.select("period").unique() for s in scans]).unique().collect()
        return sorted({p[:4] for p in periods["period"].to_list()})

    def _legal_entities(self, inputs: Mapping[str, Any]) -> pl.DataFrame:
        info = inputs["legal_entities"]
        scan = self._reader.scan(str(info["uri"]), int(info["delta_version"]))
        return (
            scan.filter(pl.col("snapshot") == pl.col("snapshot").max())
            .select(
                "recipient_code",
                "legal_nature_description",
                "cnae_code",
                "cnae_description",
                "cnae_section_code",
                "cnae_section_description",
                "municipality_name_source",
                "uf",
            )
            .collect()
        )

    def _geography(self, inputs: Mapping[str, Any]) -> tuple[pl.DataFrame, pl.DataFrame]:
        ref = inputs["reference"]
        dtb = self._reader.scan(str(ref["uri"]), int(ref["delta_version"])).collect()
        year = str(dtb["reference_year"].max())
        dtb = dtb.filter(pl.col("reference_year") == year)
        observed = pl.DataFrame(
            schema={"level_id": pl.String, "code": pl.String, "name": pl.String}
        )
        try:
            geography = build_dim_geography(
                dtb,
                observed,
                reference=f"{ref['dataset_id']} {year} (Silver v{ref['delta_version']})",
                uf_abbreviations=dict(contas.UF_ABBREVIATIONS),
            )
            return geography, build_ancestor_bridge(geography)
        except GeographyError as exc:
            raise GoldBuildError(str(exc)) from exc

    def _set_checks(
        self,
        small: Mapping[str, pl.DataFrame],
        batched: Mapping[str, _Table],
        class_conflicts: int,
    ) -> list[CheckResult]:
        geography = small[DIM_GEOGRAPHY.name]
        periods = small[DIM_PERIOD.name]
        out: list[CheckResult] = []
        for name in (AGG_CONTAS_TERRITORY.name, AGG_RECIPIENT_RANK.name):
            keys = pl.concat(batched[name].geography).unique()
            out.append(
                foreign_key(
                    f"fk.{name}.geography", keys, "geography_key", geography, "geography_key"
                )
            )
        out.append(
            foreign_key(
                "fk.period_status.period",
                small[AGG_CONTAS_PERIOD_STATUS.name],
                "period",
                periods,
                "period",
            )
        )
        natural = small[DIM_RECIPIENT.name].select("recipient_code", "recipient_name")
        duplicated = int(natural.is_duplicated().sum())
        ids = int(small[DIM_RECIPIENT.name]["recipient_id"].is_duplicated().sum())
        out.append(
            CheckResult(
                "dim_recipient.unique.recipient_id",
                CheckStatus.FAIL if ids else CheckStatus.PASS,
                "identificador estável único",
                observed=ids,
            )
        )
        out.append(
            CheckResult(
                "dim_recipient.unique.natural_key",
                CheckStatus.FAIL if duplicated else CheckStatus.PASS,
                f"código + nome únicos ({natural.height} favorecidos)",
                observed=duplicated,
            )
        )
        out.append(
            CheckResult(
                "dim_recipient.class_between_lenses",
                CheckStatus.WARN if class_conflicts else CheckStatus.PASS,
                (
                    f"{class_conflicts} favorecidos com classes diferentes entre as lentes "
                    "(vale a da lente A)"
                ),
                observed=class_conflicts,
            )
        )
        return out

    # ------------------------------------------------------------- escrita

    def _schema_plan(self, contracts: Mapping[str, Contract]) -> dict[str, bool]:
        """Confere o schema de cada tabela existente antes da primeira escrita."""
        evolve: dict[str, bool] = {}
        for name, contract in contracts.items():
            uri = self.table_uri(name)
            evolve[name] = False
            if DeltaTable.is_deltatable(uri):
                comparison = compare_schema(pl.scan_delta(uri).collect_schema(), contract)
                if comparison.change is SchemaChange.INCOMPATIBLE:
                    if name not in self._reset_schema:
                        msg = f"{name}: mudança de schema incompatível: {list(comparison.details)}"
                        raise GoldBuildError(msg)
                    continue
                evolve[name] = comparison.change is SchemaChange.COMPATIBLE_ADDITION
        return evolve

    def _add(self, run: _Run, name: str, frame: pl.DataFrame) -> None:
        table = run.batched[name]
        table.checks.add(frame)
        if "geography_key" in frame.columns:
            table.geography.append(_detached(frame.select("geography_key").unique()))
        table.rows += frame.height
        self._write(
            run.build,
            name,
            frame,
            table.contract,
            run.evolve,
            mode="append" if table.writes else "overwrite",
            rows=table.rows,
        )
        table.writes += 1

    def _write(
        self,
        build: GoldBuild,
        name: str,
        frame: pl.DataFrame,
        contract: Contract,
        evolve: Mapping[str, bool],
        *,
        mode: Literal["overwrite", "append"],
        rows: int | None = None,
    ) -> None:
        result = self._writer.write(
            self.table_uri(name),
            frame,
            run_id=build.build_id,
            mode=mode,
            partition_by=list(contract.partition_by),
            evolve_schema=evolve[name],
            overwrite_schema=name in self._reset_schema and mode == "overwrite",
        )
        build.tables[name] = GoldTable(
            table_id=name,
            storage_uri=result.table_uri,
            delta_version=result.version,
            contract_version=contract.version,
            rows=frame.height if rows is None else rows,
        )


# ------------------------------------------------------------------ verificações


def _totals(fact: pl.DataFrame, measure: str) -> pl.DataFrame:
    return _detached(fact.group_by("period").agg(pl.col(measure).sum().alias("value")))


def _fidelity(
    lens: str, silver: pl.LazyFrame, fact: pl.DataFrame, measures: Sequence[str]
) -> pl.DataFrame:
    """Soma e linhas por mês: Silver x fato (igualdade exata em decimal)."""
    source = (
        silver.group_by("period")
        .agg(*[pl.col(m).sum().alias(f"{m}_silver") for m in measures], pl.len().alias("lines"))
        .with_columns(contas.gold_period())
        .collect(engine="streaming")
    )
    gold = fact.group_by("period").agg(
        *[pl.col(m).sum().alias(f"{m}_gold") for m in measures],
        pl.col("source_lines").sum().cast(pl.UInt32).alias("lines_gold"),
    )
    joined = source.join(gold, on="period", how="full", coalesce=True)
    differs = pl.any_horizontal(
        *[pl.col(f"{m}_silver").ne_missing(pl.col(f"{m}_gold")) for m in measures],
        pl.col("lines").cast(pl.Int64).ne_missing(pl.col("lines_gold").cast(pl.Int64)),
    )
    return _detached(joined.filter(differs).select(pl.lit(lens).alias("lens"), "period"))


def _fidelity_result(problems: pl.DataFrame) -> CheckResult:
    if problems.height:
        return CheckResult(
            "fidelity.silver_sums",
            CheckStatus.FAIL,
            f"{problems.height} meses com soma ou linhas diferentes da Silver",
            observed=problems.rows()[:50],
        )
    return CheckResult(
        "fidelity.silver_sums",
        CheckStatus.PASS,
        "soma e linhas de cada mês iguais às da Silver nas três lentes",
    )


def _partition_check(agg: pl.DataFrame) -> pl.DataFrame:
    """Em cada território e mês, as categorias de cada dimensão somam o total."""
    total = agg.filter(pl.col("dimension_id") == "total").select(
        "lens", "geography_key", "period", pl.col("value").alias("total")
    )
    sums = (
        agg.filter(pl.col("dimension_id") != "total")
        .group_by("lens", "geography_key", "period", "dimension_id")
        .agg(pl.col("value").sum())
    )
    bad = sums.join(total, on=["lens", "geography_key", "period"], how="left").filter(
        pl.col("value").ne_missing(pl.col("total"))
    )
    return _detached(bad.select("lens", "geography_key", "period", "dimension_id").head(50))


def _partition_result(bad: pl.DataFrame) -> CheckResult:
    if bad.height:
        return CheckResult(
            "agg_contas_territory.dimensions_sum_to_total",
            CheckStatus.FAIL,
            f"{bad.height} combinações com detalhamento que não soma o total",
            observed=bad.rows()[:50],
        )
    return CheckResult(
        "agg_contas_territory.dimensions_sum_to_total",
        CheckStatus.PASS,
        "cada dimensão do detalhar por soma o total do território e mês",
    )


def _reconciliation_results(status: pl.DataFrame) -> list[CheckResult]:
    """Meses incompletos da lente A: aviso (é a fonte), com o detalhe por mês."""
    incomplete = status.filter((pl.col("lens") == "A") & (pl.col("status") == "incompleto"))
    detail = {
        row["period"]: {
            "falta_bi": round(float(row["shortfall"]) / 1e9, 2),
            "fracao": round(float(row["shortfall_share"]), 4),
            "acoes": row["missing_actions"],
        }
        for row in incomplete.iter_rows(named=True)
    }
    return [
        CheckResult(
            "reconciliation.transfers_vs_execution",
            CheckStatus.WARN if detail else CheckStatus.PASS,
            (
                f"{len(detail)} meses com transferências abaixo do pago na execução "
                f"(acima de {contas.INCOMPLETE_SHARE:.0%})"
                if detail
                else "todos os meses fechados conferem com a execução"
            ),
            observed=detail or None,
        )
    ]


def _complements(rows: pl.DataFrame) -> pl.DataFrame:
    """Valor do complemento do FPM por mês (período Gold), para a situação do mês."""
    return (
        rows.group_by("period")
        .agg(pl.col("value").sum().cast(VALUE_DTYPE).alias("complement_value"))
        .with_columns(contas.gold_period())
    )


def _fpm_results(fpm: contas.FpmComplement) -> list[CheckResult]:
    """Conferência do FPM com o Tesouro (ADR-0038).

    Bloqueiam: complemento negativo (o Tesouro abaixo da lente A num mês complementado) e
    município complementado sem linha de FPM da prefeitura para copiar. Avisam: diferenças
    nos meses não complementados (ficam registradas em ``agg_fpm_reconciliation``).
    """
    rec = fpm.reconciliation
    by_status = dict(rec["status"].value_counts().rows())
    months = (
        fpm.rows.group_by("period")
        .agg(pl.col("value").sum().cast(pl.Float64), pl.len())
        .sort("period")
    )
    divergent = rec.filter(pl.col("status") == "divergente")
    return [
        CheckResult(
            "fpm.treasury_complement",
            CheckStatus.FAIL if fpm.negative.height else CheckStatus.PASS,
            (
                f"{months.height} meses complementados pelo Tesouro, "
                f"{fpm.rows.height} linhas; {fpm.negative.height} negativas"
            ),
            observed=fpm.negative.rows()[:20] or None,
            details={
                p: {"bi": round(v / 1e9, 4), "municipios": n} for p, v, n in months.iter_rows()
            },
        ),
        CheckResult(
            "fpm.complement_template",
            CheckStatus.FAIL if fpm.without_template.height else CheckStatus.PASS,
            f"{fpm.without_template.height} municípios sem linha de FPM para copiar",
            observed=fpm.without_template.rows()[:20] or None,
        ),
        CheckResult(
            "fpm.reconciliation",
            CheckStatus.WARN if divergent.height else CheckStatus.PASS,
            (
                f"{by_status.get('conferido', 0)} conferidos ao centavo, "
                f"{by_status.get('complementado', 0)} complementados, "
                f"{divergent.height} divergentes"
            ),
            observed=divergent.select("period", "municipality_id").rows()[:20] or None,
            details={"status": by_status},
        ),
    ]
