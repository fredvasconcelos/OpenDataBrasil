"""Contrato comum dos conectores (§7.2).

Correspondência com o contrato conceitual:

========================  ==================================================
§7.2                      Implementação
========================  ==================================================
``discover()``            ``Connector.discover``
``describe(dataset_id)``  ``Connector.describe``
``plan(dataset_id, …)``   ``Connector.plan`` (recebe o watermark do framework)
``extract(plan)``         ``Connector.extract`` (um ``ExtractionRequest`` por vez)
``validate_raw(…)``       ``Connector.validate_raw``
``get_watermark(…)``      ``IngestionRegistry.get_watermark``: o framework persiste
                          o watermark, e o conector só o interpreta no ``plan``
``healthcheck()``         ``Connector.healthcheck``
========================  ==================================================

Conectores declaram ``capabilities`` em vez de simular recursos que a fonte não tem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Protocol

from odb_ingestion.config import DatasetConfig, SourceConfig
from odb_ingestion.http import DownloadResult, HttpClient


class Capability(StrEnum):
    """Recursos que um conector oferece."""

    DISCOVER_CONFIGURED = "discover_configured"  # lista apenas datasets configurados
    PARTITIONED = "partitioned"  # divide a extração em várias requisições
    INCREMENTAL_CHECKSUM = "incremental_checksum"  # detecta mudança comparando checksums
    CONDITIONAL_REQUEST = "conditional_request"  # usa ETag / If-Modified-Since
    HEALTHCHECK = "healthcheck"


@dataclass(frozen=True, slots=True)
class PartitionState:
    """Último estado válido de uma partição."""

    checksum_sha256: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    source_version: str | None = None


@dataclass(frozen=True, slots=True)
class Watermark:
    """Estado conhecido de todas as partições de um dataset."""

    partitions: Mapping[str, PartitionState] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    """Uma requisição planejada."""

    partition_key: str
    url: str
    artifact_name: str
    reference_period: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    max_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ExtractionPlan:
    """Plano de extração de um dataset."""

    dataset_id: str
    requests: tuple[ExtractionRequest, ...]
    notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """Representação serializável, registrada em ``operations.ingestion.plan``."""
        return {
            "dataset_id": self.dataset_id,
            "requests": [asdict(r) for r in self.requests],
            "notes": list(self.notes),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Resultado da validação técnica de um artefato bruto."""

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    stats: Mapping[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        """True quando não há erros."""
        return not self.errors

    def to_json(self) -> dict[str, Any]:
        """Representação serializável."""
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Disponibilidade da fonte."""

    ok: bool
    detail: str
    latency_ms: float | None = None


class Connector(Protocol):
    """Interface implementada por todos os conectores."""

    connector_type: ClassVar[str]
    capabilities: ClassVar[frozenset[Capability]]
    source: SourceConfig

    def discover(self) -> list[DatasetConfig]:
        """Datasets que o conector sabe obter."""
        ...

    def describe(self, dataset_id: str) -> DatasetConfig:
        """Metadados e parâmetros de um dataset."""
        ...

    def plan(
        self, dataset_id: str, http: HttpClient, watermark: Watermark, *, full: bool = False
    ) -> ExtractionPlan:
        """Requisições necessárias; ``full`` ignora o watermark."""
        ...

    def extract(self, request: ExtractionRequest, http: HttpClient, dest: Path) -> DownloadResult:
        """Executa uma requisição e grava o corpo bruto em ``dest``."""
        ...

    def validate_raw(
        self, dataset_id: str, request: ExtractionRequest, result: DownloadResult
    ) -> ValidationResult:
        """Validação técnica do artefato bruto (sem transformá-lo)."""
        ...

    def healthcheck(self, http: HttpClient) -> HealthStatus:
        """Verifica se a fonte responde."""
        ...


class BaseConnector(ABC):
    """Base dos conectores: ``discover``, ``describe`` e ``extract`` padrão."""

    connector_type: ClassVar[str] = "base"
    capabilities: ClassVar[frozenset[Capability]] = frozenset({Capability.DISCOVER_CONFIGURED})

    def __init__(self, source: SourceConfig, datasets: list[DatasetConfig]) -> None:
        """Valida os parâmetros de todos os datasets da fonte na construção."""
        self.source = source
        self._datasets = {d.id: d for d in datasets}
        for dataset in datasets:
            self.validate_params(dataset)

    def validate_params(self, dataset: DatasetConfig) -> None:  # noqa: B027 - gancho opcional
        """Valida ``dataset.params``. Subclasses lançam ``ConfigError``."""

    def discover(self) -> list[DatasetConfig]:
        """Datasets configurados para esta fonte."""
        return list(self._datasets.values())

    def describe(self, dataset_id: str) -> DatasetConfig:
        """Configuração do dataset."""
        try:
            return self._datasets[dataset_id]
        except KeyError as exc:
            msg = f"dataset {dataset_id} não pertence à fonte {self.source.id}"
            raise KeyError(msg) from exc

    def extract(self, request: ExtractionRequest, http: HttpClient, dest: Path) -> DownloadResult:
        """Download direto da URL planejada."""
        return http.download(
            request.url, dest, headers=request.headers, max_bytes=request.max_bytes
        )

    @abstractmethod
    def plan(
        self, dataset_id: str, http: HttpClient, watermark: Watermark, *, full: bool = False
    ) -> ExtractionPlan:
        """Requisições necessárias; ``full`` ignora o watermark."""

    @abstractmethod
    def validate_raw(
        self, dataset_id: str, request: ExtractionRequest, result: DownloadResult
    ) -> ValidationResult:
        """Validação técnica do artefato bruto."""

    @abstractmethod
    def healthcheck(self, http: HttpClient) -> HealthStatus:
        """Verifica se a fonte responde."""
