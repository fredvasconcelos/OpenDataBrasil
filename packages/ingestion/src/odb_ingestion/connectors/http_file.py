"""Conector genérico de arquivo estático via HTTP(S).

Usa requisição condicional (``If-None-Match`` / ``If-Modified-Since``) quando o
servidor fornece ``ETag``/``Last-Modified``. Uma resposta 304 não gera download
(``not_modified``). Sem esses cabeçalhos, a deduplicação por checksum evita
bytes repetidos na Bronze.

Validação: limites de tamanho e, para ZIP, integridade do arquivo e presença
dos membros esperados.
"""

from __future__ import annotations

import fnmatch
import time
import zipfile
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from odb_ingestion.config import ConfigError, DatasetConfig
from odb_ingestion.contract import (
    BaseConnector,
    Capability,
    ExtractionPlan,
    ExtractionRequest,
    HealthStatus,
    ValidationResult,
    Watermark,
)
from odb_ingestion.http import DownloadResult, HttpClient, HttpError

PARTITION = "file"


class HttpFileParams(BaseModel):
    """Parâmetros de um dataset de arquivo único."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str = Field(pattern=r"^https://")
    artifact_name: str
    reference_period: str | None = None
    format: Literal["zip", "binary"] = "binary"
    expected_members: tuple[str, ...] = ()
    min_bytes: int = Field(default=1, ge=1)
    max_bytes: int = Field(default=200 * 1024**2, ge=1)


class HttpFileConnector(BaseConnector):
    """Um arquivo por dataset."""

    connector_type: ClassVar[str] = "http_file"
    capabilities: ClassVar[frozenset[Capability]] = frozenset(
        {
            Capability.DISCOVER_CONFIGURED,
            Capability.CONDITIONAL_REQUEST,
            Capability.INCREMENTAL_CHECKSUM,
            Capability.HEALTHCHECK,
        }
    )

    def validate_params(self, dataset: DatasetConfig) -> None:
        """Valida os parâmetros do dataset."""
        self.params(dataset)

    @staticmethod
    def params(dataset: DatasetConfig) -> HttpFileParams:
        """Parâmetros tipados."""
        try:
            return HttpFileParams.model_validate(dataset.params)
        except ValidationError as exc:
            msg = f"{dataset.id}: parâmetros http_file inválidos: {exc}"
            raise ConfigError(msg) from exc

    def plan(
        self, dataset_id: str, http: HttpClient, watermark: Watermark, *, full: bool = False
    ) -> ExtractionPlan:
        """Uma requisição, condicional ao último estado válido (salvo com ``full``)."""
        params = self.params(self.describe(dataset_id))
        headers: dict[str, str] = {}
        state = watermark.partitions.get(PARTITION)
        if state is not None and not full:
            if state.etag:
                headers["If-None-Match"] = state.etag
            if state.last_modified:
                headers["If-Modified-Since"] = state.last_modified
        request = ExtractionRequest(
            partition_key=PARTITION,
            url=params.url,
            artifact_name=params.artifact_name,
            reference_period=params.reference_period,
            headers=headers,
            max_bytes=params.max_bytes,
        )
        notes = ("requisição condicional",) if headers else ()
        return ExtractionPlan(dataset_id=dataset_id, requests=(request,), notes=notes)

    def validate_raw(
        self, dataset_id: str, request: ExtractionRequest, result: DownloadResult
    ) -> ValidationResult:
        """Tamanho e, para ZIP, integridade e membros esperados."""
        params = self.params(self.describe(dataset_id))
        if result.path is None:
            return ValidationResult(errors=("artefato sem conteúdo",))
        errors: list[str] = []
        warnings: list[str] = []
        stats: dict[str, object] = {"size_bytes": result.size_bytes}
        if result.size_bytes < params.min_bytes:
            errors.append(f"{result.size_bytes} bytes, mínimo esperado {params.min_bytes}")
        if params.format == "zip":
            if not zipfile.is_zipfile(result.path):
                return ValidationResult(
                    errors=(*errors, "conteúdo não é um ZIP válido"), stats=stats
                )
            with zipfile.ZipFile(result.path) as archive:
                corrupted = archive.testzip()
                names = archive.namelist()
            if corrupted is not None:
                errors.append(f"membro corrompido no ZIP: {corrupted}")
            for pattern in params.expected_members:
                if not fnmatch.filter(names, pattern):
                    errors.append(f"membro esperado ausente: {pattern}")
            stats["members"] = names
            content_type = result.content_type or ""
            if "zip" not in content_type:
                warnings.append(f"content-type {content_type!r} não indica ZIP")
        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings), stats=stats)

    def healthcheck(self, http: HttpClient) -> HealthStatus:
        """Busca a URL base da fonte."""
        started = time.perf_counter()
        try:
            http.get_bytes(self.source.base_url, max_bytes=5 * 1024**2)
        except HttpError as exc:
            return HealthStatus(ok=False, detail=str(exc))
        latency = round((time.perf_counter() - started) * 1000, 1)
        return HealthStatus(ok=True, detail=f"{self.source.base_url} acessível", latency_ms=latency)
