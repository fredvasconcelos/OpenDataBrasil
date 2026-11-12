"""Construção da camada Silver (§9).

Fluxo de ``SilverBuilder.build(dataset_id)``:

1. resolve as entradas pelo watermark: o último estado válido de cada
   partição, com o artefato Bronze ``stored`` que contém os bytes;
2. confere o SHA-256 de cada arquivo Bronze antes de ler;
3. calcula uma impressão digital (checksums + versão do contrato + parâmetros).
   Se for igual à da última execução bem-sucedida, a execução termina
   ``skipped`` e **nenhuma versão Delta nova é criada**;
4. transforma (Polars) e roda as verificações de qualidade. Um ``fail``
   bloqueia a escrita;
5. compara o schema da tabela existente com o contrato. Uma mudança
   incompatível bloqueia;
6. substitui por inteiro a partição lógica do dataset (``replace_where``),
   para que linhas removidas pela fonte também saiam da Silver.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

import polars as pl
from deltalake import DeltaTable

from odb_common.logging import log_context
from odb_common.storage import LakehouseLayout, Layer, uri_to_local_path
from odb_ingestion.bronze import sha256_file
from odb_ingestion.config import DatasetConfig, SourceCatalog
from odb_ingestion.connectors.sidra import SidraConnector
from odb_lakehouse import DeltaReader, DeltaWriter
from odb_processing.contracts import (
    DTB_MUNICIPALITY,
    SIDRA_OBSERVATION,
    TERRITORIAL_MESH,
    Contract,
    SchemaChange,
    compare_schema,
)
from odb_processing.datasus import SIM_FIELDS, UF_CODES, read_dbc, sim_deaths
from odb_processing.parsers import (
    Lineage,
    MeshSpec,
    extract_member,
    parse_dtb_municipalities,
    parse_sidra,
    parse_territorial_mesh,
)
from odb_processing.quality import (
    CheckResult,
    blocking,
    dtb_checks,
    mesh_checks,
    sidra_checks,
    sinesp_checks,
)
from odb_processing.sinesp import (
    Unavailable,
    VdeReport,
    load_coverage,
    normalize_name,
    read_vde,
    sinesp_observations,
)

logger = logging.getLogger(__name__)

RunStatus = Literal["succeeded", "skipped", "failed"]
_SIM_FILE = re.compile(r"DO(?P<uf>[A-Za-z]{2})(?P<year>\d{4})\.dbc", re.IGNORECASE)

CONTRACT_BY_TRANSFORMER = {
    "sidra_observation": SIDRA_OBSERVATION,
    # Agregados do SIM por município, no mesmo contrato de observação do SIDRA.
    "datasus_sim_do": SIDRA_OBSERVATION,
    # SINESP VDE (MJSP): município x evento x mês, no mesmo contrato (ADR-0012).
    "sinesp_vde": SIDRA_OBSERVATION,
    "dtb_municipality": DTB_MUNICIPALITY,
    "territorial_mesh": TERRITORIAL_MESH,
}


class SilverBuildError(RuntimeError):
    """Falha que impede a construção da Silver."""


@dataclass(frozen=True, slots=True)
class SilverInput:
    """Artefato Bronze vigente de uma partição."""

    partition_key: str
    artifact_id: str
    ingestion_id: str
    storage_uri: str
    checksum_sha256: str
    source_url: str
    retrieved_at: datetime
    reference_period: str | None


@dataclass(frozen=True, slots=True)
class PreviousRun:
    """Última execução bem-sucedida de um dataset."""

    run_id: str
    input_fingerprint: str
    target_uri: str
    delta_version: int | None


class SilverRegistry(Protocol):
    """Persistência de entradas, execuções e resultados (implementação: ``odb_catalog.silver``)."""

    def current_inputs(self, dataset_id: str) -> list[SilverInput]:
        """Artefatos Bronze vigentes (watermark), apontando para os bytes ``stored``."""
        ...

    def last_success(self, dataset_id: str) -> PreviousRun | None:
        """Última execução Silver ``succeeded`` ou ``skipped`` com versão Delta."""
        ...

    def start_run(
        self, run: SilverRun, *, pipeline_run_id: str | None, inputs: Sequence[SilverInput]
    ) -> None:
        """Registra a execução como ``running``."""
        ...

    def finish_run(self, run: SilverRun) -> None:
        """Finaliza a execução com estado, versão e estatísticas."""
        ...

    def record_checks(self, run_id: str, dataset_id: str, results: Sequence[CheckResult]) -> None:
        """Grava os resultados de qualidade."""
        ...


@dataclass
class SilverRun:
    """Estado e resultado de uma execução Silver."""

    run_id: str
    dataset_id: str
    target_uri: str
    contract: str
    contract_version: str
    code_version: str
    input_fingerprint: str = ""
    status: RunStatus | Literal["running"] = "running"
    delta_version: int | None = None
    rows: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    error: str | None = None

    def stats(self) -> dict[str, Any]:
        """Estatísticas da execução."""
        counts: dict[str, int] = {}
        for c in self.checks:
            counts[c.status.value] = counts.get(c.status.value, 0) + 1
        return {"rows": self.rows, "checks": counts}


class SilverBuilder:
    """Constrói tabelas Silver a partir dos artefatos Bronze vigentes."""

    def __init__(
        self,
        catalog: SourceCatalog,
        layout: LakehouseLayout,
        writer: DeltaWriter,
        registry: SilverRegistry,
        *,
        code_version: str = "unknown",
        config_dir: Path | None = None,
    ) -> None:
        """Recebe o catálogo de fontes, o lakehouse, o escritor Delta e o registro.

        ``config_dir`` é o diretório das fontes (``configs/sources``), base dos arquivos
        auxiliares citados na configuração Silver (ex.: ``coverage_file``).
        """
        self._catalog = catalog
        self._layout = layout
        self._writer = writer
        self._registry = registry
        self._code_version = code_version
        self._config_dir = config_dir
        self._reader = DeltaReader()

    # ------------------------------------------------------------- configuração

    def transformer(self, dataset: DatasetConfig) -> str:
        """Transformação Silver declarada para o dataset."""
        name = dataset.silver.get("transformer")
        if name not in CONTRACT_BY_TRANSFORMER:
            msg = f"{dataset.id}: transformação Silver ausente ou desconhecida: {name!r}"
            raise SilverBuildError(msg)
        return str(name)

    def contract_for(self, dataset: DatasetConfig) -> Contract:
        """Contrato da tabela de destino."""
        return CONTRACT_BY_TRANSFORMER[self.transformer(dataset)]

    def target_uri(self, dataset: DatasetConfig) -> str:
        """URI da tabela Silver do dataset."""
        institution = self._catalog.source_institution[dataset.source]
        return self._layout.table_uri(Layer.SILVER, institution, self.contract_for(dataset).name)

    def build_order(self, dataset_ids: Sequence[str]) -> list[str]:
        """Referências territoriais (DTB) antes das tabelas que dependem delas."""
        datasets = [self._catalog.dataset(d) for d in dataset_ids]
        return [d.id for d in sorted(datasets, key=lambda d: "territorial_reference" in d.silver)]

    # ------------------------------------------------------------- execução

    def build_many(
        self, dataset_ids: Sequence[str], *, pipeline_run_id: str | None = None, force: bool = False
    ) -> list[SilverRun]:
        """Constrói cada dataset de forma isolada, na ordem de dependência."""
        return [
            self.build(d, pipeline_run_id=pipeline_run_id, force=force)
            for d in self.build_order(dataset_ids)
        ]

    def build(
        self, dataset_id: str, *, pipeline_run_id: str | None = None, force: bool = False
    ) -> SilverRun:
        """Constrói a Silver de um dataset. Erros são registrados no ``SilverRun``."""
        dataset = self._catalog.dataset(dataset_id)
        contract = self.contract_for(dataset)
        run = SilverRun(
            run_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            target_uri=self.target_uri(dataset),
            contract=contract.name,
            contract_version=contract.version,
            code_version=self._code_version,
        )
        inputs = self._inputs(dataset)
        run.input_fingerprint = self._fingerprint(dataset, contract, inputs)
        self._registry.start_run(run, pipeline_run_id=pipeline_run_id, inputs=inputs)
        with log_context(silver_run_id=run.run_id, dataset_id=dataset_id):
            try:
                self._execute(dataset, contract, inputs, run, force=force)
            except Exception as exc:
                run.status = "failed"
                run.error = f"{type(exc).__name__}: {exc}"
                logger.exception("silver build failed")
            finally:
                if run.checks:
                    self._registry.record_checks(run.run_id, dataset_id, run.checks)
                self._registry.finish_run(run)
        return run

    def _inputs(self, dataset: DatasetConfig) -> list[SilverInput]:
        inputs = self._registry.current_inputs(dataset.id)
        if self.transformer(dataset) == "sidra_observation":
            # Só as partições da configuração atual (níveis e divisão por variável).
            pattern = SidraConnector.params(dataset).partition_pattern()
            inputs = [i for i in inputs if pattern.fullmatch(i.partition_key)]
        return sorted(inputs, key=lambda i: i.partition_key)

    def _fingerprint(
        self, dataset: DatasetConfig, contract: Contract, inputs: Sequence[SilverInput]
    ) -> str:
        payload = {
            "contract": f"{contract.name}:{contract.version}",
            "silver": dataset.silver,
            "inputs": [(i.partition_key, i.checksum_sha256) for i in inputs],
            # Arquivo auxiliar (tabela de cobertura): mudar o conteúdo refaz a Silver.
            "coverage": self._coverage(dataset)[1],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _execute(
        self,
        dataset: DatasetConfig,
        contract: Contract,
        inputs: Sequence[SilverInput],
        run: SilverRun,
        *,
        force: bool,
    ) -> None:
        if not inputs:
            msg = f"nenhum artefato Bronze vigente para {dataset.id}; execute a ingestão"
            raise SilverBuildError(msg)
        previous = self._registry.last_success(dataset.id)
        if (
            not force
            and previous is not None
            and previous.input_fingerprint == run.input_fingerprint
            and previous.delta_version is not None
            and self._reader.has_version(run.target_uri, previous.delta_version)
        ):
            run.status = "skipped"
            run.delta_version = previous.delta_version
            logger.info("silver unchanged", extra={"delta_version": previous.delta_version})
            return
        for item in inputs:
            path = Path(uri_to_local_path(item.storage_uri))
            if not path.is_file() or sha256_file(path) != item.checksum_sha256:
                msg = f"artefato Bronze ausente ou corrompido: {item.storage_uri}"
                raise SilverBuildError(msg)

        processed_at = datetime.now(UTC)
        transformer = self.transformer(dataset)
        if transformer == "sidra_observation":
            frame, partition = self._sidra_frame(dataset, inputs, run, processed_at)
            run.checks = sidra_checks(
                frame,
                contract,
                dataset.silver.get("additive_variables", {}),
                *self._reference(dataset),
            )
        elif transformer == "datasus_sim_do":
            reference_ids, reference_label = self._reference(dataset)
            frame, partition = self._sim_frame(dataset, inputs, run, processed_at, reference_ids)
            # Sem reconciliação entre níveis: a UF inclui óbitos de município ignorado.
            run.checks = sidra_checks(frame, contract, {}, reference_ids, reference_label)
        elif transformer == "sinesp_vde":
            reference_ids, reference_label = self._reference(dataset)
            frame, partition, report = self._sinesp_frame(dataset, inputs, run, processed_at)
            # Sem reconciliação entre níveis: a UF inclui linhas sem município.
            run.checks = [
                *sidra_checks(frame, contract, {}, reference_ids, reference_label),
                *sinesp_checks(report),
            ]
        elif transformer == "territorial_mesh":
            frame, partition = self._mesh_frame(dataset, inputs, run, processed_at)
            reference_ids, reference_label = self._reference(dataset)
            expected = dataset.silver.get("expected_count")
            run.checks = mesh_checks(
                frame,
                contract,
                expected_count=None if expected is None else int(expected),
                reference_ids=reference_ids,
                reference_label=reference_label,
            )
        else:
            frame, partition = self._dtb_frame(dataset, inputs, run, processed_at)
            run.checks = dtb_checks(frame, contract)
        run.rows = frame.height

        failures = blocking(run.checks)
        if failures:
            msg = "verificações bloqueantes falharam: " + ", ".join(c.check_id for c in failures)
            raise SilverBuildError(msg)

        evolve = False
        if DeltaTable.is_deltatable(run.target_uri):
            existing = pl.scan_delta(run.target_uri).collect_schema()
            comparison = compare_schema(existing, contract)
            if comparison.change is SchemaChange.INCOMPATIBLE:
                msg = f"mudança de schema incompatível: {list(comparison.details)}"
                raise SilverBuildError(msg)
            evolve = comparison.change is SchemaChange.COMPATIBLE_ADDITION
        result = self._writer.write(
            run.target_uri,
            frame,
            run_id=run.run_id,
            mode="overwrite",
            partition_by=list(contract.partition_by),
            replace_where=partition,
            evolve_schema=evolve,
        )
        run.delta_version = result.version
        run.status = "succeeded"

    def _lineage(self, item: SilverInput, run: SilverRun, processed_at: datetime) -> Lineage:
        return Lineage(
            bronze_artifact_id=item.artifact_id,
            bronze_checksum_sha256=item.checksum_sha256,
            source_url=item.source_url,
            retrieved_at=item.retrieved_at,
            ingestion_id=item.ingestion_id,
            silver_run_id=run.run_id,
            processed_at=processed_at,
        )

    def _sidra_frame(
        self,
        dataset: DatasetConfig,
        inputs: Sequence[SilverInput],
        run: SilverRun,
        processed_at: datetime,
    ) -> tuple[pl.DataFrame, dict[str, str]]:
        params = SidraConnector.params(dataset)
        frames = [
            parse_sidra(
                Path(uri_to_local_path(item.storage_uri)).read_bytes(),
                table_id=params.table,
                lineage=self._lineage(item, run, processed_at),
                territory_dim=params.territory_dimension,
                variable_dim=params.variable_dimension,
                period_dim=params.period_dimension,
            )
            for item in inputs
        ]
        return pl.concat(frames), {"table_id": params.table}

    def _sim_frame(
        self,
        dataset: DatasetConfig,
        inputs: Sequence[SilverInput],
        run: SilverRun,
        processed_at: datetime,
        reference_ids: set[str] | None,
    ) -> tuple[pl.DataFrame, dict[str, str]]:
        """Arquivos ``DO<UF><ano>.dbc`` do SIM → óbitos por município e UF (marginais)."""
        if not reference_ids:
            msg = f"{dataset.id}: o SIM exige a DTB na Silver (códigos de 6 para 7 dígitos)"
            raise SilverBuildError(msg)
        municipalities = {code[:6]: code for code in reference_ids}
        table_id = str(dataset.silver.get("table_id", "SIM-DORES"))
        frames = []
        for item in inputs:
            m = _SIM_FILE.fullmatch(item.partition_key)
            if m is None:
                msg = f"arquivo fora do padrão DO<UF><ano>.dbc: {item.partition_key}"
                raise SilverBuildError(msg)
            records = read_dbc(Path(uri_to_local_path(item.storage_uri)), SIM_FIELDS)
            frames.append(
                sim_deaths(
                    records,
                    uf=m["uf"].upper(),
                    year=m["year"],
                    municipalities=municipalities,
                    table_id=table_id,
                    lineage=self._lineage(item, run, processed_at),
                )
            )
        return pl.concat(frames), {"table_id": table_id}

    def _sinesp_frame(
        self,
        dataset: DatasetConfig,
        inputs: Sequence[SilverInput],
        run: SilverRun,
        processed_at: datetime,
    ) -> tuple[pl.DataFrame, dict[str, str], VdeReport]:
        """Planilha anual do SINESP VDE → observações por município e UF (marginais)."""
        if len(inputs) != 1:
            msg = f"SINESP VDE espera 1 planilha vigente, encontradas {len(inputs)}"
            raise SilverBuildError(msg)
        item = inputs[0]
        year = item.reference_period
        if not year:
            msg = f"{dataset.id}: planilha do SINESP VDE sem período de referência"
            raise SilverBuildError(msg)
        names = self._municipality_names(dataset)
        # Uma partição por ano: os datasets são anuais e a escrita substitui a partição.
        table_id = f"{dataset.silver.get('table_id', 'SINESP-VDE')}-{year}"
        frame, report = sinesp_observations(
            read_vde(Path(uri_to_local_path(item.storage_uri))),
            year=year,
            uf_codes=UF_CODES,
            municipalities=names,
            table_id=table_id,
            lineage=self._lineage(item, run, processed_at),
            unavailable=self._coverage(dataset)[0],
        )
        return frame, {"table_id": table_id}, report

    def _coverage(self, dataset: DatasetConfig) -> tuple[list[Unavailable], str | None]:
        """Tabela de cobertura do dataset (``coverage_file``), se houver, e o seu SHA-256."""
        name = dataset.silver.get("coverage_file")
        if not name:
            return [], None
        if self._config_dir is None:
            msg = f"{dataset.id}: coverage_file exige o diretório de configuração das fontes"
            raise SilverBuildError(msg)
        path = self._config_dir / str(name)
        if not path.is_file():
            msg = f"{dataset.id}: tabela de cobertura não encontrada: {path}"
            raise SilverBuildError(msg)
        return load_coverage(path)

    def _municipality_names(self, dataset: DatasetConfig) -> dict[tuple[str, str], str]:
        """(sigla da UF, nome normalizado) → código IBGE, da DTB vigente na Silver.

        Inclui ``aliases`` da configuração Silver (grafias antigas publicadas pela fonte),
        sempre apontando para um código que existe na DTB.
        """
        ref_id = dataset.silver.get("territorial_reference")
        if not ref_id:
            msg = f"{dataset.id}: o SINESP VDE exige a DTB (casamento por nome)"
            raise SilverBuildError(msg)
        ref = self._catalog.dataset(str(ref_id))
        previous = self._registry.last_success(ref.id)
        if previous is None or previous.delta_version is None:
            msg = f"{dataset.id}: DTB sem Silver vigente; construa {ref.id} antes"
            raise SilverBuildError(msg)
        dtb = (
            self._reader.scan(self.target_uri(ref), previous.delta_version)
            .select("reference_year", "uf_id", "municipality_id", "municipality_name")
            .collect()
        )
        dtb = dtb.filter(pl.col("reference_year") == dtb["reference_year"].max())
        sigla = {code: uf for uf, code in UF_CODES.items()}
        names: dict[tuple[str, str], str] = {}
        for row in dtb.iter_rows(named=True):
            names[(sigla[str(row["uf_id"])], normalize_name(str(row["municipality_name"])))] = str(
                row["municipality_id"]
            )
        codes = set(names.values())
        for alias, code in dict(dataset.silver.get("aliases", {})).items():
            uf, _, name = str(alias).partition("/")
            if str(code) not in codes:
                msg = f"{dataset.id}: alias {alias} aponta para código fora da DTB: {code}"
                raise SilverBuildError(msg)
            names[(uf, normalize_name(name))] = str(code)
        return names

    def _dtb_frame(
        self,
        dataset: DatasetConfig,
        inputs: Sequence[SilverInput],
        run: SilverRun,
        processed_at: datetime,
    ) -> tuple[pl.DataFrame, dict[str, str]]:
        if len(inputs) != 1:
            msg = f"DTB espera 1 artefato vigente, encontrados {len(inputs)}"
            raise SilverBuildError(msg)
        item = inputs[0]
        reference_year = item.reference_period
        if not reference_year:
            msg = "artefato da DTB sem período de referência"
            raise SilverBuildError(msg)
        member, content = extract_member(
            Path(uri_to_local_path(item.storage_uri)), str(dataset.silver["member"])
        )
        frame = parse_dtb_municipalities(
            content,
            member=member,
            reference_year=reference_year,
            lineage=self._lineage(item, run, processed_at),
        )
        return frame, {"reference_year": reference_year}

    def _mesh_frame(
        self,
        dataset: DatasetConfig,
        inputs: Sequence[SilverInput],
        run: SilverRun,
        processed_at: datetime,
    ) -> tuple[pl.DataFrame, dict[str, str]]:
        if len(inputs) != 1:
            msg = f"malha espera 1 artefato vigente, encontrados {len(inputs)}"
            raise SilverBuildError(msg)
        item = inputs[0]
        if not item.reference_period:
            msg = f"{dataset.id}: artefato da malha sem período de referência"
            raise SilverBuildError(msg)
        cfg = dataset.silver
        try:
            spec = MeshSpec(
                dataset_id=dataset.id,
                member=str(cfg["member"]),
                level_id=str(cfg["level"]),
                code_field=str(cfg["code_field"]),
                name_field=str(cfg["name_field"]),
                uf_field=None if cfg.get("uf_field") is None else str(cfg["uf_field"]),
            )
        except KeyError as exc:
            msg = f"{dataset.id}: configuração Silver da malha incompleta: {exc}"
            raise SilverBuildError(msg) from exc
        frame = parse_territorial_mesh(
            Path(uri_to_local_path(item.storage_uri)),
            spec,
            reference_year=item.reference_period,
            lineage=self._lineage(item, run, processed_at),
        )
        return frame, {"dataset_id": dataset.id}

    def _reference(self, dataset: DatasetConfig) -> tuple[set[str] | None, str]:
        """Códigos de município da referência territorial, na versão Silver vigente."""
        ref_id = dataset.silver.get("territorial_reference")
        if not ref_id:
            return None, "sem referência"
        ref = self._catalog.dataset(str(ref_id))
        previous = self._registry.last_success(ref.id)
        uri = self.target_uri(ref)
        if previous is None or previous.delta_version is None:
            return None, ref.id
        frame = (
            self._reader.scan(uri, previous.delta_version)
            .select("reference_year", "municipality_id")
            .collect()
        )
        latest = str(frame["reference_year"].max())
        ids = set(frame.filter(pl.col("reference_year") == latest)["municipality_id"].to_list())
        return ids, f"{ref.id} {latest} (Delta v{previous.delta_version})"


def results_to_json(results: Sequence[CheckResult]) -> list[Mapping[str, Any]]:
    """Representação serializável dos resultados."""
    return [
        {
            "check_id": r.check_id,
            "status": r.status.value,
            "message": r.message,
            "observed": r.observed,
            "expected": r.expected,
            "details": dict(r.details),
        }
        for r in results
    ]
