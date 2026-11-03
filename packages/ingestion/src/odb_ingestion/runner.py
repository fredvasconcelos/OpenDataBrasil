"""Execução de ingestões (§7.4, §7.5).

Para cada dataset:

1. registra a ingestão como ``running`` e salva o plano;
2. para cada requisição: download no staging → ``validate_raw`` →
   * inválido: cópia para a quarentena e registro ``quarantined``;
   * checksum já armazenado: registro ``reused`` apontando para os bytes
     existentes, sem gravar nada na Bronze;
   * novo: cópia verificada para a Bronze e registro ``stored``;
   * ``304``: registro ``not_modified``;
   * erro HTTP: registro ``failed``;
3. atualiza o watermark **somente** se todas as requisições tiverem sucesso.
   Caso contrário, a ingestão termina ``failed`` e a última versão válida
   continua sendo a referência.

A falha de um dataset nunca interrompe os demais (``run_many``).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from odb_common.logging import log_context
from odb_ingestion.bronze import BronzeStore, snapshot_segment
from odb_ingestion.config import DatasetConfig, SourceCatalog
from odb_ingestion.contract import (
    BaseConnector,
    ExtractionPlan,
    ExtractionRequest,
    PartitionState,
    Watermark,
)
from odb_ingestion.http import DownloadResult, HttpClient, HttpError

logger = logging.getLogger(__name__)

ArtifactStatus = Literal["stored", "reused", "not_modified", "quarantined", "failed"]


class DuplicateContentError(RuntimeError):
    """Outro registro ``stored`` com o mesmo checksum foi gravado concorrentemente."""


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """Referência a bytes já presentes na Bronze."""

    artifact_id: str
    storage_uri: str


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """Linha de ``operations.bronze_artifact``."""

    artifact_id: str
    ingestion_id: str
    dataset_id: str
    partition_key: str
    source_url: str
    retrieved_at: datetime
    status: ArtifactStatus
    license_id: str
    access_classification: str
    http_status: int | None = None
    content_type: str | None = None
    file_size_bytes: int | None = None
    checksum_sha256: str | None = None
    storage_uri: str | None = None
    reused_from: str | None = None
    source_version: str | None = None
    reference_period: str | None = None
    validation: Mapping[str, Any] = field(default_factory=dict)
    response_headers: Mapping[str, str] = field(default_factory=dict)
    error: str | None = None


class IngestionRegistry(Protocol):
    """Persistência dos metadados de ingestão (implementação: ``odb_catalog.ingestion``)."""

    def sync_catalog(self, catalog: SourceCatalog) -> None:
        """Insere ou atualiza instituições, licenças, fontes e datasets."""
        ...

    def start_ingestion(
        self, ingestion_id: str, dataset_id: str, run_id: str | None, parameters: Mapping[str, Any]
    ) -> None:
        """Registra a ingestão como ``running``."""
        ...

    def save_plan(self, ingestion_id: str, plan: Mapping[str, Any]) -> None:
        """Guarda o plano de extração."""
        ...

    def find_stored(self, checksum_sha256: str) -> StoredArtifact | None:
        """Artefato ``stored`` com o mesmo conteúdo, se existir."""
        ...

    def record_artifact(self, record: ArtifactRecord) -> None:
        """Insere o artefato. Lança ``DuplicateContentError`` em conflito de deduplicação."""
        ...

    def get_watermark(self, dataset_id: str) -> Watermark:
        """Último estado válido das partições do dataset."""
        ...

    def update_watermark(
        self, dataset_id: str, partitions: Mapping[str, tuple[PartitionState, str | None]]
    ) -> None:
        """Atualiza partições (estado + artifact_id) atomicamente."""
        ...

    def finish_ingestion(
        self,
        ingestion_id: str,
        status: Literal["succeeded", "failed"],
        stats: Mapping[str, Any],
        error: str | None,
    ) -> None:
        """Finaliza a ingestão."""
        ...


@dataclass
class IngestionReport:
    """Resumo de uma ingestão."""

    ingestion_id: str
    dataset_id: str
    status: Literal["succeeded", "failed"] = "failed"
    planned: int = 0
    counts: dict[str, int] = field(default_factory=dict)
    bytes_downloaded: int = 0
    bytes_stored: int = 0
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    def bump(self, status: ArtifactStatus) -> None:
        """Conta um artefato por estado."""
        self.counts[status] = self.counts.get(status, 0) + 1

    def stats(self) -> dict[str, Any]:
        """Estatísticas registradas em ``operations.ingestion.stats``."""
        return {
            "planned": self.planned,
            "counts": dict(self.counts),
            "bytes_downloaded": self.bytes_downloaded,
            "bytes_stored": self.bytes_stored,
        }


HttpFactory = Callable[[BaseConnector], HttpClient]


class IngestionRunner:
    """Orquestra conectores, Bronze e registro."""

    def __init__(
        self,
        catalog: SourceCatalog,
        connectors: Mapping[str, BaseConnector],
        bronze: BronzeStore,
        registry: IngestionRegistry,
        http_factory: HttpFactory,
        *,
        capacity_check: Callable[[], None] = lambda: None,
    ) -> None:
        """``capacity_check`` lança exceção quando o disco atinge o limite de bloqueio."""
        self._catalog = catalog
        self._connectors = connectors
        self._bronze = bronze
        self._registry = registry
        self._http_factory = http_factory
        self._capacity_check = capacity_check

    def connector_for(self, dataset: DatasetConfig) -> BaseConnector:
        """Conector da fonte do dataset."""
        return self._connectors[dataset.source]

    def sync_catalog(self) -> None:
        """Registra a configuração atual no catálogo (idempotente)."""
        self._registry.sync_catalog(self._catalog)

    def plan(self, dataset_id: str, *, full: bool = False) -> ExtractionPlan:
        """Plano sem executar downloads de dados (apenas descoberta)."""
        dataset = self._catalog.dataset(dataset_id)
        connector = self.connector_for(dataset)
        watermark = Watermark() if full else self._registry.get_watermark(dataset_id)
        with self._http_factory(connector) as http:
            return connector.plan(dataset_id, http, watermark, full=full)

    def run_many(
        self, dataset_ids: Sequence[str], *, run_id: str | None = None, full: bool = False
    ) -> list[IngestionReport]:
        """Ingere cada dataset de forma isolada."""
        self.sync_catalog()
        return [self.run(d, run_id=run_id, full=full, sync=False) for d in dataset_ids]

    def run(
        self, dataset_id: str, *, run_id: str | None = None, full: bool = False, sync: bool = True
    ) -> IngestionReport:
        """Ingere um dataset. Nunca propaga exceções do dataset; o resultado vai no relatório."""
        if sync:
            self.sync_catalog()
        dataset = self._catalog.dataset(dataset_id)
        ingestion_id = str(uuid.uuid4())
        report = IngestionReport(ingestion_id=ingestion_id, dataset_id=dataset_id)
        started_at = datetime.now(UTC)
        self._registry.start_ingestion(ingestion_id, dataset_id, run_id, {"full": full})
        with log_context(ingestion_id=ingestion_id, dataset_id=dataset_id):
            try:
                if not dataset.enabled:
                    msg = f"dataset {dataset_id} desabilitado na configuração"
                    raise RuntimeError(msg)
                self._capacity_check()
                self._execute(dataset, ingestion_id, started_at, report, full=full)
            except Exception as exc:
                report.status = "failed"
                report.error = f"{type(exc).__name__}: {exc}"
                logger.exception("ingestion failed")
            finally:
                self._bronze.cleanup_staging(ingestion_id)
                self._registry.finish_ingestion(
                    ingestion_id, report.status, report.stats(), report.error
                )
            logger.info("ingestion finished", extra={"status": report.status, **report.stats()})
        return report

    def _execute(
        self,
        dataset: DatasetConfig,
        ingestion_id: str,
        started_at: datetime,
        report: IngestionReport,
        *,
        full: bool,
    ) -> None:
        connector = self.connector_for(dataset)
        watermark = Watermark() if full else self._registry.get_watermark(dataset.id)
        snapshot = snapshot_segment(started_at, ingestion_id)
        staging = self._bronze.staging_dir(ingestion_id)
        pending: dict[str, tuple[PartitionState, str | None]] = {}
        failures: list[str] = []

        with self._http_factory(connector) as http:
            plan = connector.plan(dataset.id, http, watermark, full=full)
            report.planned = len(plan.requests)
            report.notes.extend(plan.notes)
            self._registry.save_plan(ingestion_id, plan.to_json())

            for index, request in enumerate(plan.requests):
                base: dict[str, Any] = {
                    "ingestion_id": ingestion_id,
                    "dataset_id": dataset.id,
                    "partition_key": request.partition_key,
                    "source_url": request.url,
                    "license_id": dataset.license,
                    "access_classification": dataset.access_classification,
                    "reference_period": request.reference_period,
                }
                dest = staging / f"{index:05d}-{request.artifact_name}"
                try:
                    result = connector.extract(request, http, dest)
                except HttpError as exc:
                    self._record(
                        report,
                        ArtifactRecord(
                            artifact_id=str(uuid.uuid4()),
                            retrieved_at=datetime.now(UTC),
                            status="failed",
                            http_status=exc.status,
                            error=str(exc)[:4000],
                            **base,
                        ),
                    )
                    failures.append(f"{request.partition_key}: {exc}")
                    continue
                report.bytes_downloaded += result.size_bytes
                if result.not_modified:
                    self._record(report, self._from_result(result, "not_modified", base))
                    continue
                state = self._handle_content(
                    connector=connector,
                    dataset=dataset,
                    request=request,
                    snapshot=snapshot,
                    result=result,
                    base=base,
                    report=report,
                )
                if state is None:
                    failures.append(f"{request.partition_key}: artefato em quarentena")
                else:
                    pending[request.partition_key] = state

        if failures:
            msg = f"{len(failures)} de {report.planned} requisições falharam: " + "; ".join(
                failures[:5]
            )
            raise RuntimeError(msg)
        if pending:
            self._registry.update_watermark(dataset.id, pending)
        report.status = "succeeded"

    def _handle_content(
        self,
        *,
        connector: BaseConnector,
        dataset: DatasetConfig,
        request: ExtractionRequest,
        snapshot: str,
        result: DownloadResult,
        base: dict[str, Any],
        report: IngestionReport,
    ) -> tuple[PartitionState, str | None] | None:
        assert result.path is not None  # noqa: S101 - garantido para status != 304
        assert result.sha256 is not None  # noqa: S101
        validation = connector.validate_raw(dataset.id, request, result)
        store_args: dict[str, Any] = {
            "source_id": dataset.source,
            "dataset_id": dataset.id,
            "snapshot": snapshot,
            "artifact_name": request.artifact_name,
            "expected_sha256": result.sha256,
        }
        if not validation.valid:
            uri = self._bronze.store(result.path, quarantine=True, **store_args)
            self._record(
                report,
                self._from_result(
                    result,
                    "quarantined",
                    base,
                    storage_uri=uri,
                    validation=validation.to_json(),
                    error="; ".join(validation.errors)[:4000],
                ),
            )
            return None

        existing = self._registry.find_stored(result.sha256)
        artifact_id = str(uuid.uuid4())
        if existing is None:
            uri = self._bronze.store(result.path, **store_args)
            record = self._from_result(
                result,
                "stored",
                base,
                artifact_id=artifact_id,
                storage_uri=uri,
                validation=validation.to_json(),
            )
            try:
                self._record(report, record)
                report.bytes_stored += result.size_bytes
            except DuplicateContentError:
                self._bronze.remove_unregistered(uri)
                existing = self._registry.find_stored(result.sha256)
                if existing is None:  # pragma: no cover - conflito sem registro visível
                    raise
        if existing is not None:
            self._record(
                report,
                self._from_result(
                    result,
                    "reused",
                    base,
                    artifact_id=artifact_id,
                    storage_uri=existing.storage_uri,
                    reused_from=existing.artifact_id,
                    validation=validation.to_json(),
                ),
            )
        state = PartitionState(
            checksum_sha256=result.sha256,
            etag=result.headers.get("etag"),
            last_modified=result.headers.get("last-modified"),
            source_version=result.headers.get("last-modified"),
        )
        return state, artifact_id

    @staticmethod
    def _from_result(
        result: DownloadResult,
        status: ArtifactStatus,
        base: Mapping[str, Any],
        *,
        artifact_id: str | None = None,
        **extra: Any,
    ) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=artifact_id or str(uuid.uuid4()),
            retrieved_at=result.retrieved_at,
            status=status,
            http_status=result.status,
            content_type=result.content_type,
            file_size_bytes=result.size_bytes if result.path else None,
            checksum_sha256=result.sha256,
            source_version=result.headers.get("last-modified"),
            response_headers=dict(result.headers),
            **base,
            **extra,
        )

    def _record(self, report: IngestionReport, record: ArtifactRecord) -> None:
        self._registry.record_artifact(record)
        report.bump(record.status)
