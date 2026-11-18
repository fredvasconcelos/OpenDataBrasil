"""Conector de arquivos em FTP público (§7.3), por exemplo a transferência de arquivos do DATASUS.

Cada dataset é um diretório e um padrão de nomes (expressão regular). Cada
arquivo que casa com o padrão é uma partição (a chave é o nome do arquivo).

* **Descoberta**: ``LIST`` do diretório. O servidor do DATASUS (Microsoft FTP
  Service) não aceita ``MLSD`` com fatos; a listagem no formato DOS traz data,
  hora e tamanho, que formam a assinatura de mudança do arquivo (o FTP não tem
  ETag).
* **Incremental**: um arquivo é baixado de novo quando é novo ou quando a
  assinatura (tamanho e data da listagem) muda. Arquivos revisados pela fonte
  (o SIM e o SINASC são revisados) entram como versão nova na Bronze; a
  deduplicação por SHA-256 evita bytes repetidos.
* **Robustez**: tempo de espera, novas tentativas com espera crescente e
  intervalo mínimo entre comandos, pela política HTTP da fonte
  (``[sources.http]``). Falhas transitórias saem como ``HttpError`` com
  ``transient=True``, para o adiamento do runner.
* **Validação**: tamanho igual ao da listagem e, para ``.dbc``, descompressão
  completa e leitura do cabeçalho DBF (detecta arquivo truncado ou corrompido).
"""

from __future__ import annotations

import ftplib
import hashlib
import re
import socket
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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

# "01-31-20  02:48PM                76107 DOAC1996.dbc" ou "<DIR>" no lugar do tamanho.
_DOS_LINE = re.compile(
    r"^(?P<date>\d{2}-\d{2}-\d{2})\s+(?P<time>\d{1,2}:\d{2}[AP]M)\s+"
    r"(?P<size><DIR>|\d+)\s+(?P<name>.+)$"
)
_TRANSIENT = (ftplib.error_temp, ftplib.error_reply, OSError, EOFError, socket.timeout)
SIGNATURE_HEADER = "last-modified"  # gravado como source_version da partição


@dataclass(frozen=True, slots=True)
class RemoteFile:
    """Arquivo listado no servidor."""

    name: str
    size: int
    modified: str  # "2020-01-31T14:48" (hora local do servidor, sem fuso)

    @property
    def signature(self) -> str:
        """Assinatura de mudança: tamanho e data da listagem."""
        return f"{self.size}|{self.modified}"


def artifact_name(remote_name: str) -> str:
    """Nome seguro na Bronze para um arquivo do FTP (§6.4: não depender do nome de terceiros).

    Minúsculo, sem acentos nem espaços, com um sufixo do SHA-1 do nome original
    para não colidir ("DOSP2008.DBC" e "dosp2008.dbc" viram nomes diferentes). O
    nome original fica na chave da partição e na URL de origem.
    """
    base, dot, ext = remote_name.rpartition(".")
    if not dot:
        base, ext = remote_name, ""
    ascii_ = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")[:80] or "arquivo"
    tag = hashlib.sha1(remote_name.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    clean_ext = re.sub(r"[^a-z0-9]", "", ext.lower())[:10]
    return f"{slug}-{tag}" + (f".{clean_ext}" if clean_ext else "")


def parse_dos_listing(lines: list[str]) -> list[RemoteFile]:
    """Arquivos de uma listagem ``LIST`` no formato DOS (diretórios ignorados)."""
    out = []
    for line in lines:
        m = _DOS_LINE.match(line.strip())
        if m is None or m["size"] == "<DIR>":
            continue
        # Hora local do servidor, sem fuso declarado: serve só de assinatura de mudança.
        stamp = datetime.strptime(f"{m['date']} {m['time']}", "%m-%d-%y %I:%M%p")  # noqa: DTZ007
        out.append(RemoteFile(m["name"], int(m["size"]), stamp.strftime("%Y-%m-%dT%H:%M")))
    return out


class FtpFilesParams(BaseModel):
    """Parâmetros de um dataset ``ftp_file``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    directory: str = Field(min_length=1)  # relativo ao caminho da URL da fonte
    pattern: str  # expressão regular do nome; o grupo "period" vira o período de referência
    # "auto": valida como .dbc os arquivos com essa extensão (maiúscula ou minúscula).
    format: Literal["dbc", "binary", "auto"] = "auto"
    min_bytes: int = Field(default=1, ge=1)
    max_bytes: int = Field(default=2 * 1024**3, ge=1)
    min_files: int = Field(default=1, ge=0)

    @field_validator("pattern")
    @classmethod
    def _regex(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            msg = f"padrão inválido: {exc}"
            raise ValueError(msg) from exc
        return value

    @property
    def regex(self) -> re.Pattern[str]:
        """Padrão compilado (o nome inteiro precisa casar)."""
        return re.compile(self.pattern)


class FtpSession:
    """Sessão FTP com ritmo, tempo de espera e novas tentativas da política da fonte."""

    def __init__(self, base_url: str, http: HttpClient) -> None:
        """``http`` fornece só a política (``http.policy``); a conexão é ``ftplib``."""
        parsed = urlparse(base_url)
        if parsed.scheme != "ftp" or not parsed.hostname:
            msg = f"URL de FTP inválida: {base_url}"
            raise ConfigError(msg)
        self.host = parsed.hostname
        self.root = parsed.path.rstrip("/")
        self.policy = http.policy
        self._ftp: ftplib.FTP | None = None
        self._last = 0.0

    def url(self, directory: str, name: str = "") -> str:
        """URL ``ftp://`` de um diretório ou arquivo."""
        path = "/".join(p.strip("/") for p in (self.root, directory, name) if p.strip("/"))
        return f"ftp://{self.host}/{path}"

    def _connect(self) -> ftplib.FTP:
        if self._ftp is None:
            ftp = ftplib.FTP(timeout=self.policy.timeout_s)
            # Nomes de arquivo e listagens do DATASUS vêm em Latin-1, não em UTF-8.
            ftp.encoding = "latin-1"
            ftp.connect(self.host, timeout=self.policy.connect_timeout_s)
            ftp.login()
            self._ftp = ftp
        return self._ftp

    def close(self) -> None:
        """Encerra a conexão (sem falhar se ela já caiu)."""
        if self._ftp is not None:
            try:
                self._ftp.quit()
            except (*_TRANSIENT, ftplib.Error):
                self._ftp.close()
            self._ftp = None

    def _run[T](self, label: str, action: Callable[[ftplib.FTP], T]) -> T:
        last_error = ""
        for attempt in range(1, self.policy.max_attempts + 1):
            wait = self.policy.min_interval_s - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                result = action(self._connect())
            except ftplib.error_perm as exc:  # recusa definitiva (550, arquivo inexistente...)
                self._last = time.monotonic()
                msg = f"{label}: {exc}"
                raise HttpError(msg, url=label) from exc
            except _TRANSIENT as exc:
                self._last = time.monotonic()
                last_error = f"{type(exc).__name__}: {exc}"
                self.close()
                if attempt < self.policy.max_attempts:
                    time.sleep(
                        min(
                            self.policy.backoff_initial_s * 2 ** (attempt - 1),
                            self.policy.backoff_max_s,
                        )
                    )
                continue
            self._last = time.monotonic()
            return result
        msg = f"{label}: falhou após {self.policy.max_attempts} tentativas ({last_error})"
        raise HttpError(msg, url=label, transient=True)

    def list(self, directory: str) -> list[RemoteFile]:
        """Arquivos do diretório."""
        path = self.url(directory).split(self.host, 1)[1]

        def action(ftp: ftplib.FTP) -> list[str]:
            lines: list[str] = []
            ftp.retrlines(f"LIST {path}", lines.append)
            return lines

        return parse_dos_listing(self._run(f"LIST {path}", action))

    def download(self, directory: str, name: str, dest: Path, max_bytes: int) -> tuple[int, str]:
        """Baixa um arquivo para ``dest``; devolve (bytes, SHA-256)."""
        path = self.url(directory, name).split(self.host, 1)[1]

        def action(ftp: ftplib.FTP) -> tuple[int, str]:
            digest = hashlib.sha256()
            size = 0
            with dest.open("wb") as fh:

                def write(chunk: bytes) -> None:
                    nonlocal size
                    size += len(chunk)
                    if size > max_bytes:
                        msg = f"{name}: passou de {max_bytes} bytes"
                        raise ftplib.error_perm(msg)
                    digest.update(chunk)
                    fh.write(chunk)

                ftp.retrbinary(f"RETR {path}", write, blocksize=1024 * 1024)
            return size, digest.hexdigest()

        return self._run(f"RETR {path}", action)


class FtpFileConnector(BaseConnector):
    """Arquivos de um diretório FTP, um por partição."""

    connector_type: ClassVar[str] = "ftp_file"
    capabilities: ClassVar[frozenset[Capability]] = frozenset(
        {
            Capability.DISCOVER_CONFIGURED,
            Capability.PARTITIONED,
            Capability.INCREMENTAL_CHECKSUM,
            Capability.HEALTHCHECK,
        }
    )

    def validate_params(self, dataset: DatasetConfig) -> None:
        """Valida os parâmetros do dataset."""
        self.params(dataset)

    @staticmethod
    def params(dataset: DatasetConfig) -> FtpFilesParams:
        """Parâmetros tipados."""
        try:
            return FtpFilesParams.model_validate(dataset.params)
        except ValidationError as exc:
            msg = f"{dataset.id}: parâmetros ftp_file inválidos: {exc}"
            raise ConfigError(msg) from exc

    def remote_files(self, dataset_id: str, http: HttpClient) -> list[RemoteFile]:
        """Arquivos do diretório que casam com o padrão do dataset."""
        params = self.params(self.describe(dataset_id))
        session = FtpSession(self.source.base_url, http)
        try:
            files = session.list(params.directory)
        finally:
            session.close()
        return sorted((f for f in files if params.regex.fullmatch(f.name)), key=lambda f: f.name)

    def plan(
        self, dataset_id: str, http: HttpClient, watermark: Watermark, *, full: bool = False
    ) -> ExtractionPlan:
        """Arquivos novos ou com assinatura diferente da última versão válida."""
        params = self.params(self.describe(dataset_id))
        files = self.remote_files(dataset_id, http)
        if len(files) < params.min_files:
            msg = f"{dataset_id}: {len(files)} arquivos com o padrão, mínimo {params.min_files}"
            raise HttpError(msg, url=params.directory)
        session = FtpSession(self.source.base_url, http)
        requests: list[ExtractionRequest] = []
        unchanged: list[str] = []
        for remote in files:
            state = watermark.partitions.get(remote.name)
            if not full and state is not None and state.source_version == remote.signature:
                unchanged.append(remote.name)
                continue
            m = params.regex.fullmatch(remote.name)
            period = m.groupdict().get("period") if m else None
            requests.append(
                ExtractionRequest(
                    partition_key=remote.name,
                    url=session.url(params.directory, remote.name),
                    artifact_name=artifact_name(remote.name),
                    reference_period=period,
                    headers={
                        "x-ftp-name": remote.name,
                        "x-ftp-directory": params.directory,
                        "x-ftp-size": str(remote.size),
                        "x-ftp-signature": remote.signature,
                    },
                    max_bytes=params.max_bytes,
                )
            )
        total = sum(f.size for f in files)
        notes = [f"{len(files)} arquivos no diretório ({total} bytes)"]
        if unchanged:
            notes.append(f"{len(unchanged)} sem mudança desde a última versão válida")
        return ExtractionPlan(
            dataset_id=dataset_id,
            requests=tuple(requests),
            notes=tuple(notes),
            metadata={"files": len(files), "bytes": total},
        )

    def _shared_session(self, http: HttpClient) -> FtpSession:
        """Conexão reaproveitada entre arquivos (um login por execução, não por arquivo).

        Se a conexão cair, a sessão reconecta sozinha na próxima tentativa.
        """
        session: FtpSession | None = getattr(self, "_session", None)
        if session is None or session.policy is not http.policy:
            if session is not None:
                session.close()
            session = FtpSession(self.source.base_url, http)
            self._session = session
        return session

    def extract(self, request: ExtractionRequest, http: HttpClient, dest: Path) -> DownloadResult:
        """Baixa o arquivo; a assinatura da listagem vira a versão da fonte."""
        directory = request.headers["x-ftp-directory"]
        session = self._shared_session(http)
        size, sha = session.download(
            directory, request.headers["x-ftp-name"], dest, request.max_bytes or 2 * 1024**3
        )
        headers = {
            SIGNATURE_HEADER: request.headers.get("x-ftp-signature", ""),
            "content-length": str(size),
            "content-type": "application/octet-stream",
        }
        return DownloadResult(
            request.url, 200, headers, datetime.now(UTC), path=dest, size_bytes=size, sha256=sha
        )

    def validate_raw(
        self, dataset_id: str, request: ExtractionRequest, result: DownloadResult
    ) -> ValidationResult:
        """Tamanho igual ao listado e, para ``.dbc``, descompressão e cabeçalho DBF."""
        params = self.params(self.describe(dataset_id))
        if result.path is None:
            return ValidationResult(errors=("artefato sem conteúdo",))
        errors: list[str] = []
        stats: dict[str, object] = {"size_bytes": result.size_bytes}
        listed = request.headers.get("x-ftp-size")
        if listed is not None and int(listed) != result.size_bytes:
            errors.append(f"{result.size_bytes} bytes baixados, {listed} na listagem")
        if result.size_bytes < params.min_bytes:
            errors.append(f"{result.size_bytes} bytes, mínimo esperado {params.min_bytes}")
        is_dbc = params.format == "dbc" or (
            params.format == "auto" and request.artifact_name.endswith(".dbc")
        )
        if is_dbc and not errors:
            try:
                stats |= dbc_summary(result.path)
            except Exception as exc:
                errors.append(f".dbc ilegível: {type(exc).__name__}: {exc}")
        return ValidationResult(errors=tuple(errors), stats=stats)

    def healthcheck(self, http: HttpClient) -> HealthStatus:
        """Lista o diretório raiz da fonte."""
        started = time.perf_counter()
        session = FtpSession(self.source.base_url, http)
        try:
            session.list("")
        except HttpError as exc:
            return HealthStatus(ok=False, detail=str(exc))
        finally:
            session.close()
        latency = round((time.perf_counter() - started) * 1000, 1)
        return HealthStatus(ok=True, detail=f"{self.source.base_url} acessível", latency_ms=latency)


def dbc_summary(path: Path) -> dict[str, object]:
    """Descomprime um ``.dbc`` (DBF + blast) e lê o cabeçalho: registros e campos."""
    import tempfile  # noqa: PLC0415

    import datasus_dbc  # noqa: PLC0415 - dependência só deste formato
    from dbfread import DBF  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        dbf = Path(tmp) / (path.stem + ".dbf")
        datasus_dbc.decompress(str(path), str(dbf))
        table = DBF(str(dbf), load=False, encoding="latin-1")
        return {
            "records": len(table),
            "fields": [f.name for f in table.fields],
            "dbf_bytes": dbf.stat().st_size,
        }
