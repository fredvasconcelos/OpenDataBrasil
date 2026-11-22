"""Conector genérico de arquivos periódicos via HTTP(S): um arquivo por período.

Cada dataset declara uma URL modelo com ``{period}`` (``AAAAMM`` no grão mensal,
``AAAA`` no anual) e o intervalo de períodos. Cada período é uma partição com
requisição condicional própria (``If-None-Match`` / ``If-Modified-Since``): no
ciclo seguinte, os meses sem mudança respondem 304 e os revisados pela fonte
voltam a ser baixados. É assim que a revisão retroativa é detectada (ADR-0030,
decisão 4: "não assumir que períodos antigos são imutáveis", §7.6).

Validação técnica, sem transformar o artefato:

* tamanho mínimo e máximo;
* ZIP íntegro e com os membros esperados;
* cabeçalho do CSV (no membro do ZIP ou no próprio arquivo) idêntico ao contrato
  declarado: colunas novas, removidas ou renomeadas vão para a quarentena antes
  de chegar à Silver (§9.3);
* SHA-256 de cada membro, registrado nas estatísticas: dois ZIPs com bytes
  diferentes e CSVs iguais indicam uma regeração sem mudança de conteúdo.

Ano corrente: ``end = "atual"`` termina no mês (ou ano) corrente, no fuso de
Brasília. A fonte regera o arquivo do mês corrente enquanto ele acontece, e uma
execução diária só baixa o que mudou (os demais respondem 304). Se o período
corrente ainda não foi publicado (dia 1º, por exemplo), o plano sonda 1 byte dele: a
resposta "objeto inexistente" do servidor (404, ou 403 ``AccessDenied`` de bucket) tira
o período do plano com uma nota. Qualquer outra recusa (como a verificação humana de
um WAF) continua sendo erro.

Nada de nenhuma fonte específica fica aqui (§3.3): URLs, membros e colunas vêm
da configuração.
"""

from __future__ import annotations

import csv
import fnmatch
import hashlib
import io
import re
import tempfile
import time
import zipfile
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import IO, ClassVar, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from odb_common.storage import StorageError, validate_filename
from odb_ingestion.config import ConfigError, DatasetConfig, SourceConfig
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

PLACEHOLDER = "{period}"
CURRENT = "atual"
_TZ = ZoneInfo("America/Sao_Paulo")
_MONTH = re.compile(r"^(\d{4})(0[1-9]|1[0-2])$")
_YEAR = re.compile(r"^\d{4}$")
# O cabeçalho cabe com folga em 64 KiB; a leitura nunca carrega o arquivo inteiro.
_HEADER_BYTES = 64 * 1024


class CsvContract(BaseModel):
    """Cabeçalho esperado de um CSV (membro de ZIP ou o próprio arquivo)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Modelo do nome do membro, com ``{period}``; vazio quando o artefato é o CSV.
    member: str = ""
    encoding: str = "utf-8"
    delimiter: str = Field(default=",", min_length=1, max_length=1)
    columns: tuple[str, ...] = Field(min_length=1)


class HttpPeriodicParams(BaseModel):
    """Parâmetros de um dataset com um arquivo por período."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url_template: str = Field(pattern=r"^https://")
    artifact_template: str
    grain: Literal["month", "year"]
    start: str
    end: str
    format: Literal["zip", "csv", "binary"] = "binary"
    expected_members: tuple[str, ...] = ()
    csv: tuple[CsvContract, ...] = ()
    min_bytes: int = Field(default=1, ge=1)
    max_bytes: int = Field(default=500 * 1024**2, ge=1)
    # O servidor pode recusar a raiz (bucket S3 responde 403): o healthcheck lê
    # um byte (``Range``) deste arquivo conhecido.
    healthcheck_url: str | None = Field(default=None, pattern=r"^https://")

    @model_validator(mode="after")
    def _check(self) -> HttpPeriodicParams:
        for name in ("url_template", "artifact_template"):
            if PLACEHOLDER not in getattr(self, name):
                msg = f"{name} precisa conter {PLACEHOLDER}"
                raise ValueError(msg)
        periods = periods_between(self.grain, self.start, resolve_end(self, _now()))
        if not periods:
            msg = f"intervalo vazio: {self.start} a {self.end}"
            raise ValueError(msg)
        try:  # o nome vai para a Bronze, que só aceita minúsculas (odb_common.storage)
            validate_filename(self.artifact_template.replace(PLACEHOLDER, periods[0]))
        except StorageError as exc:
            raise ValueError(str(exc)) from exc
        if self.format == "binary" and self.csv:
            msg = "contrato csv exige format zip ou csv"
            raise ValueError(msg)
        if self.format == "zip" and any(not c.member for c in self.csv):
            msg = "no format zip, cada contrato csv indica o membro"
            raise ValueError(msg)
        if self.format == "csv" and (len(self.csv) > 1 or any(c.member for c in self.csv)):
            msg = "no format csv, há um contrato só, sem membro"
            raise ValueError(msg)
        return self


def _now() -> datetime:
    return datetime.now(_TZ)


def current_period(grain: Literal["month", "year"], now: datetime) -> str:
    """Período corrente no fuso de Brasília: ``AAAAMM`` ou ``AAAA``."""
    local = now.astimezone(_TZ)
    return f"{local.year:04d}{local.month:02d}" if grain == "month" else f"{local.year:04d}"


def resolve_end(params: HttpPeriodicParams, now: datetime) -> str:
    """O fim configurado, com ``atual`` trocado pelo período corrente."""
    return current_period(params.grain, now) if params.end == CURRENT else params.end


def _not_published(exc: HttpError) -> bool:
    """Resposta de objeto inexistente: 404 ou o 403 ``AccessDenied`` de um bucket S3."""
    not_found = 404
    forbidden = 403
    return exc.status == not_found or (exc.status == forbidden and "AccessDenied" in str(exc))


def periods_between(grain: Literal["month", "year"], start: str, end: str) -> list[str]:
    """Períodos de ``start`` a ``end``, inclusive, no formato da URL (AAAAMM ou AAAA)."""
    pattern = _MONTH if grain == "month" else _YEAR
    for value in (start, end):
        if not pattern.match(value):
            unit = "AAAAMM" if grain == "month" else "AAAA"
            msg = f"período {value!r} fora do formato {unit}"
            raise ValueError(msg)
    if grain == "year":
        return [str(y) for y in range(int(start), int(end) + 1)]
    out: list[str] = []
    year, month = int(start[:4]), int(start[4:])
    while f"{year:04d}{month:02d}" <= end:
        out.append(f"{year:04d}{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)  # noqa: PLR2004
    return out


def reference_period(grain: Literal["month", "year"], period: str) -> str:
    """Período de referência legível: ``2024-01`` ou ``2024``."""
    return f"{period[:4]}-{period[4:]}" if grain == "month" else period


class HttpPeriodicConnector(BaseConnector):
    """Um arquivo por período (mês ou ano), cada um uma partição."""

    connector_type: ClassVar[str] = "http_periodic"
    capabilities: ClassVar[frozenset[Capability]] = frozenset(
        {
            Capability.DISCOVER_CONFIGURED,
            Capability.PARTITIONED,
            Capability.CONDITIONAL_REQUEST,
            Capability.INCREMENTAL_CHECKSUM,
            Capability.HEALTHCHECK,
        }
    )

    def __init__(
        self,
        source: SourceConfig,
        datasets: list[DatasetConfig],
        *,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        """``clock`` define o período corrente (``end = "atual"``); injetável nos testes."""
        super().__init__(source, datasets)
        self.clock = clock

    def validate_params(self, dataset: DatasetConfig) -> None:
        """Valida os parâmetros do dataset."""
        self.params(dataset)

    @staticmethod
    def params(dataset: DatasetConfig) -> HttpPeriodicParams:
        """Parâmetros tipados."""
        try:
            return HttpPeriodicParams.model_validate(dataset.params)
        except ValidationError as exc:
            msg = f"{dataset.id}: parâmetros http_periodic inválidos: {exc}"
            raise ConfigError(msg) from exc

    def plan(
        self, dataset_id: str, http: HttpClient, watermark: Watermark, *, full: bool = False
    ) -> ExtractionPlan:
        """Uma requisição por período, condicional ao último estado válido da partição."""
        params = self.params(self.describe(dataset_id))
        end = resolve_end(params, self.clock())
        periods = periods_between(params.grain, params.start, end)
        notes: list[str] = []
        latest = periods[-1]
        # Período corrente nunca visto: pode ainda não existir na fonte.
        if (
            params.end == CURRENT
            and latest not in watermark.partitions
            and not self._published(http, params.url_template.replace(PLACEHOLDER, latest))
        ):
            notes.append(f"{latest} ainda não publicado na fonte; entra numa próxima execução")
            periods = periods[:-1]
        requests: list[ExtractionRequest] = []
        conditional = 0
        for period in periods:
            headers: dict[str, str] = {}
            state = watermark.partitions.get(period)
            if state is not None and not full:
                if state.etag:
                    headers["If-None-Match"] = state.etag
                if state.last_modified:
                    headers["If-Modified-Since"] = state.last_modified
            conditional += bool(headers)
            requests.append(
                ExtractionRequest(
                    partition_key=period,
                    url=params.url_template.replace(PLACEHOLDER, period),
                    artifact_name=params.artifact_template.replace(PLACEHOLDER, period),
                    reference_period=reference_period(params.grain, period),
                    headers=headers,
                    max_bytes=params.max_bytes,
                )
            )
        if conditional:
            notes.append(f"{conditional} requisições condicionais")
        return ExtractionPlan(
            dataset_id=dataset_id,
            requests=tuple(requests),
            notes=tuple(notes),
            metadata={
                "grain": params.grain,
                "start": params.start,
                "end": params.end,
                "resolved_end": periods[-1] if periods else None,
            },
        )

    @staticmethod
    def _published(http: HttpClient, url: str) -> bool:
        """Lê 1 byte (``Range``); objeto inexistente é False, outra recusa é erro."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                http.download(
                    url, Path(tmp) / "probe", headers={"Range": "bytes=0-0"}, max_bytes=1024**2
                )
        except HttpError as exc:
            if _not_published(exc):
                return False
            raise
        return True

    def extract(self, request: ExtractionRequest, http: HttpClient, dest: Path) -> DownloadResult:
        """Download da URL do período; status diferente de 200 e 304 é erro HTTP.

        Uma página de desafio ("Human Verification") pode chegar com 202. Tratá-la como
        erro, e não como artefato inválido, permite ao runner parar a fonte
        (``halt_on_status``) em vez de mandá-la à quarentena e seguir pedindo.
        """
        result = super().extract(request, http, dest)
        if result.status not in (200, 304):
            if result.path is not None:
                result.path.unlink(missing_ok=True)
            msg = f"HTTP {result.status} inesperado em {request.url} (esperado 200 ou 304)"
            raise HttpError(msg, url=request.url, status=result.status)
        return result

    def validate_raw(
        self, dataset_id: str, request: ExtractionRequest, result: DownloadResult
    ) -> ValidationResult:
        """Tamanho, integridade do ZIP, membros esperados e cabeçalho do CSV."""
        params = self.params(self.describe(dataset_id))
        if result.path is None:
            return ValidationResult(errors=("artefato sem conteúdo",))
        period = request.partition_key
        errors: list[str] = []
        warnings: list[str] = []
        stats: dict[str, object] = {"size_bytes": result.size_bytes, "period": period}
        if result.size_bytes < params.min_bytes:
            errors.append(f"{result.size_bytes} bytes, mínimo esperado {params.min_bytes}")
        if params.format == "csv":
            with result.path.open("rb") as handle:
                errors.extend(_check_header(handle, params.csv[0], result.path.name))
        elif params.format == "zip":
            _validate_zip(result.path, params, period, errors, stats)
            content_type = result.content_type or ""
            if "zip" not in content_type and "octet-stream" not in content_type:
                warnings.append(f"content-type {content_type!r} não indica ZIP")
        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings), stats=stats)

    def healthcheck(self, http: HttpClient) -> HealthStatus:
        """Lê 1 byte de um arquivo conhecido (``healthcheck_url``) ou a URL base."""
        urls = [
            p.healthcheck_url
            for d in self.discover()
            if (p := self.params(d)).healthcheck_url is not None
        ]
        url = urls[0] if urls else self.source.base_url
        started = time.perf_counter()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                http.download(
                    url, Path(tmp) / "health", headers={"Range": "bytes=0-0"}, max_bytes=1024**2
                )
        except HttpError as exc:
            return HealthStatus(ok=False, detail=str(exc))
        latency = round((time.perf_counter() - started) * 1000, 1)
        return HealthStatus(ok=True, detail=f"{url} acessível", latency_ms=latency)


def _validate_zip(
    path: Path,
    params: HttpPeriodicParams,
    period: str,
    errors: list[str],
    stats: dict[str, object],
) -> None:
    """Integridade, membros esperados, cabeçalhos e SHA-256 de cada membro."""
    if not zipfile.is_zipfile(path):
        errors.append("conteúdo não é um ZIP válido")
        return
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        stats["members"] = names
        member_sha: dict[str, str] = {}
        try:
            for name in names:
                member_sha[name] = _sha256(archive.open(name))
        except (zipfile.BadZipFile, OSError) as exc:
            # A leitura confere o CRC de cada membro (o mesmo que ``testzip``).
            errors.append(f"membro corrompido no ZIP: {exc}")
            return
        stats["member_sha256"] = member_sha
        for pattern in params.expected_members:
            if not fnmatch.filter(names, pattern.replace(PLACEHOLDER, period)):
                errors.append(f"membro esperado ausente: {pattern.replace(PLACEHOLDER, period)}")
        for contract in params.csv:
            member = contract.member.replace(PLACEHOLDER, period)
            if member not in names:
                errors.append(f"membro do contrato ausente: {member}")
                continue
            with archive.open(member) as handle:
                errors.extend(_check_header(handle, contract, member))


def _sha256(handle: IO[bytes]) -> str:
    digest = hashlib.sha256()
    with handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_line(handle: IO[bytes]) -> bytes:
    head = handle.read(_HEADER_BYTES)
    return head.split(b"\n", 1)[0]


def _check_header(handle: IO[bytes], contract: CsvContract, name: str) -> Iterator[str]:
    """Erros de cabeçalho: ordem e nomes iguais ao contrato, sem inferência."""
    raw = _first_line(handle)
    try:
        line = raw.decode(contract.encoding).lstrip("﻿").rstrip("\r")
    except UnicodeDecodeError:
        yield f"{name}: cabeçalho não decodifica como {contract.encoding}"
        return
    found = tuple(next(csv.reader(io.StringIO(line), delimiter=contract.delimiter), []))
    if found == contract.columns:
        return
    expected = set(contract.columns)
    added = [c for c in found if c not in expected]
    removed = [c for c in contract.columns if c not in set(found)]
    if added or removed:
        yield (
            f"{name}: cabeçalho diverge do contrato (novas: {added[:10]}; ausentes: {removed[:10]})"
        )
    else:
        yield f"{name}: colunas do contrato em outra ordem"
