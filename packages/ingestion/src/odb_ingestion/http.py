"""Cliente HTTP com timeouts, novas tentativas, respeito a 429 e ritmo por host (§7.4).

Downloads são gravados em streaming num arquivo de staging, com SHA-256
calculado durante a escrita e limite de tamanho. Nenhum mecanismo de bloqueio da
fonte é contornado: ``Retry-After`` é respeitado e falhas 4xx (exceto 429) não
são repetidas.
"""

from __future__ import annotations

import hashlib
import logging
import random
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from odb_ingestion.config import HttpPolicy

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
# Cabeçalhos de resposta preservados nos metadados do artefato.
KEPT_HEADERS = ("content-type", "content-length", "last-modified", "etag", "date", "cache-control")


class HttpError(RuntimeError):
    """Falha definitiva de uma requisição (após as tentativas permitidas).

    ``transient`` indica falha que pode passar com o tempo (timeout, conexão,
    429 ou 5xx esgotados), e não uma recusa da fonte (4xx).
    """

    def __init__(
        self, message: str, *, url: str, status: int | None = None, transient: bool = False
    ) -> None:
        """Guarda a URL, o status HTTP, quando houver, e se a falha é transitória."""
        super().__init__(message)
        self.url = url
        self.status = status
        self.transient = transient


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """Resultado de um download (``path`` é None quando o status é 304)."""

    url: str
    status: int
    headers: Mapping[str, str]
    retrieved_at: datetime
    path: Path | None = None
    size_bytes: int = 0
    sha256: str | None = None
    attempts: int = 1

    @property
    def not_modified(self) -> bool:
        """True quando o servidor respondeu 304."""
        return self.status == httpx.codes.NOT_MODIFIED

    @property
    def content_type(self) -> str | None:
        """``Content-Type`` informado pelo servidor."""
        return self.headers.get("content-type")


def _retry_after_seconds(value: str | None, now: datetime) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    return max(0.0, (target - now).total_seconds())


@dataclass
class _HostGate:
    lock: threading.Lock = field(default_factory=threading.Lock)
    last: float | None = None


class HttpClient:
    """Cliente síncrono com política por fonte."""

    def __init__(
        self,
        policy: HttpPolicy,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        """``transport``, ``sleep``, ``clock`` e ``rng`` são injetáveis para testes."""
        self.policy = policy
        self._sleep = sleep
        self._clock = clock
        self._rng = rng or random.Random()  # noqa: S311 - jitter, não criptografia
        self._gates: dict[str, _HostGate] = {}
        self._gates_lock = threading.Lock()
        self._client = httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(policy.timeout_s, connect=policy.connect_timeout_s),
            headers={"User-Agent": policy.user_agent},
            follow_redirects=True,
        )

    def close(self) -> None:
        """Fecha as conexões."""
        self._client.close()

    def __enter__(self) -> HttpClient:
        """Suporte a ``with``."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Fecha ao sair do bloco."""
        self.close()

    # ------------------------------------------------------------- ritmo e tentativas

    def _gate(self, url: str) -> _HostGate:
        host = urlparse(url).netloc
        with self._gates_lock:
            return self._gates.setdefault(host, _HostGate())

    def _wait_turn(self, gate: _HostGate) -> None:
        if gate.last is not None:
            remaining = self.policy.min_interval_s - (self._clock() - gate.last)
            if remaining > 0:
                self._sleep(remaining)
        gate.last = self._clock()

    def _backoff(self, attempt: int) -> float:
        base = min(self.policy.backoff_initial_s * 2.0 ** (attempt - 1), self.policy.backoff_max_s)
        return base + self._rng.uniform(0, base * 0.25)

    def _request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        handle: Callable[[httpx.Response, int], DownloadResult],
    ) -> DownloadResult:
        gate = self._gate(url)
        last_error = "sem tentativa"
        for attempt in range(1, self.policy.max_attempts + 1):
            with gate.lock:
                self._wait_turn(gate)
                try:
                    with self._client.stream(method, url, headers=dict(headers)) as response:
                        if response.status_code not in RETRYABLE_STATUS:
                            if response.is_error:
                                body = response.read()[:500].decode("utf-8", errors="replace")
                                msg = f"HTTP {response.status_code} em {url}: {body.strip()}"
                                raise HttpError(msg, url=url, status=response.status_code)
                            return handle(response, attempt)
                        status = response.status_code
                        retry_after = _retry_after_seconds(
                            response.headers.get("retry-after"), datetime.now(UTC)
                        )
                except httpx.TransportError as exc:
                    status, retry_after = None, None
                    last_error = f"{type(exc).__name__}: {exc}"
                else:
                    last_error = f"HTTP {status}"
            if attempt == self.policy.max_attempts:
                break
            delay = self._backoff(attempt)
            if retry_after is not None:
                if retry_after > self.policy.max_retry_after_s:
                    msg = (
                        f"{url}: Retry-After de {retry_after:.0f}s excede o máximo "
                        f"permitido ({self.policy.max_retry_after_s:.0f}s)"
                    )
                    raise HttpError(msg, url=url, status=status, transient=True)
                delay = max(delay, retry_after)
            logger.warning(
                "http retry",
                extra={"url": url, "attempt": attempt, "reason": last_error, "delay_s": delay},
            )
            self._sleep(delay)
        msg = f"{url}: falhou após {self.policy.max_attempts} tentativas ({last_error})"
        raise HttpError(msg, url=url, status=status, transient=True)

    # ------------------------------------------------------------- operações

    def download(
        self,
        url: str,
        dest: Path,
        *,
        headers: Mapping[str, str] | None = None,
        max_bytes: int | None = None,
    ) -> DownloadResult:
        """Grava o corpo em ``dest`` (criado de forma exclusiva) e calcula o SHA-256."""
        limit = min(max_bytes or self.policy.max_bytes, self.policy.max_bytes)

        def handle(response: httpx.Response, attempt: int) -> DownloadResult:
            kept = {k: v for k in KEPT_HEADERS if (v := response.headers.get(k)) is not None}
            retrieved_at = datetime.now(UTC)
            if response.status_code == httpx.codes.NOT_MODIFIED:
                return DownloadResult(url, 304, kept, retrieved_at, attempts=attempt)
            digest = hashlib.sha256()
            size = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            out = dest.open("xb")  # falha se já existir; nada a limpar nesse caso
            try:
                with out:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        size += len(chunk)
                        if size > limit:
                            msg = f"{url}: resposta excede o limite de {limit} bytes"
                            raise HttpError(msg, url=url, status=response.status_code)
                        digest.update(chunk)
                        out.write(chunk)
            except BaseException:
                dest.unlink(missing_ok=True)  # remove apenas o arquivo criado acima
                raise
            return DownloadResult(
                url,
                response.status_code,
                kept,
                retrieved_at,
                path=dest,
                size_bytes=size,
                sha256=digest.hexdigest(),
                attempts=attempt,
            )

        return self._request("GET", url, headers or {}, handle)

    def get_bytes(self, url: str, *, max_bytes: int = 10 * 1024**2) -> bytes:
        """Corpo pequeno em memória (descoberta, healthcheck)."""
        captured: list[bytes] = []

        def handle(response: httpx.Response, attempt: int) -> DownloadResult:
            body = response.read()
            if len(body) > max_bytes:
                msg = f"{url}: resposta excede o limite de {max_bytes} bytes"
                raise HttpError(msg, url=url, status=response.status_code)
            captured.append(body)
            return DownloadResult(
                url, response.status_code, {}, datetime.now(UTC), attempts=attempt
            )

        self._request("GET", url, {}, handle)
        return captured[0]
