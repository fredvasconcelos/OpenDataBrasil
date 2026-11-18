"""``odb metrics aggregate``: soma o log de acesso do Caddy no ``odb_metrics`` (ADR-0027).

Roda na Vitrine (serviço ``metrics-aggregator`` do ``compose.yaml``). O Caddy grava o log
sem IP e o roda de hora em hora (``roll_interval``); o tique do healthcheck garante uma
escrita por intervalo, sem a qual a rotação não acontece. A cada ciclo:

1. lê cada arquivo já rodado (``access-*.log``; o ``access.log`` ativo fica para depois);
2. classifica e soma por dia, evento, país, UF, rota, indicador, formato e origem;
3. grava as somas e o nome do arquivo numa transação só (``MetricsWriter.record``);
4. apaga o arquivo.

Arquivos com mais de 23 horas que não puderam ser somados (banco fora do ar, arquivo
corrompido) são apagados assim mesmo: o log bruto nunca passa de 24 horas.
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Annotated, Protocol

import typer

from odb_catalog.access_metrics import AccessKey, MetricsWriter, metrics_engine
from odb_cli.access_log import aggregate
from odb_common.logging import configure_logging
from odb_common.settings import load_settings

logger = logging.getLogger("odb.metrics")
metrics_app = typer.Typer(no_args_is_help=True, help="Métricas de acesso da Vitrine (ADR-0027).")

MAX_AGE_S = 23 * 3600
ACTIVE = "access.log"


class Recorder(Protocol):
    """O que o agregador precisa do banco (``MetricsWriter`` ou um dublê nos testes)."""

    def record(self, file_name: str, sha256: str, lines: int, counts: dict[AccessKey, int]) -> bool:
        """Grava as somas; ``False`` se o arquivo já tinha sido somado."""
        ...


@dataclass
class CycleReport:
    """Resumo de um ciclo (só contagens: nada do conteúdo do log)."""

    files: int = 0
    lines: int = 0
    invalid: int = 0
    counted: int = 0
    already: int = 0
    discarded: list[str] = field(default_factory=list)
    error: str | None = None


def rolled_files(log_dir: Path) -> list[Path]:
    """Arquivos já rodados pelo Caddy, do mais antigo ao mais novo."""
    found = [
        p
        for p in log_dir.glob("access-*.log*")
        if p.is_file() and p.name != ACTIVE and p.suffix in {".log", ".gz"}
    ]
    return sorted(found, key=lambda p: p.name)


def _read(path: Path) -> bytes:
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def run_cycle(log_dir: Path, recorder: Recorder, *, now: float | None = None) -> CycleReport:
    """Um ciclo do agregador sobre ``log_dir``."""
    report = CycleReport()
    clock = time.time() if now is None else now
    pending: list[Path] = []
    for path in rolled_files(log_dir):
        if report.error is not None:
            pending.append(path)
            continue
        try:
            data = _read(path)
        except (OSError, EOFError, gzip.BadGzipFile) as exc:
            # Arquivo ainda sendo compactado ou corrompido: tenta de novo no próximo ciclo.
            logger.warning("arquivo do log ilegível", extra={"file": path.name, "error": str(exc)})
            pending.append(path)
            continue
        counts, lines, invalid = aggregate(data.splitlines())
        try:
            fresh = recorder.record(
                path.name, hashlib.sha256(data).hexdigest(), lines, dict(counts)
            )
        except Exception as exc:
            report.error = f"{type(exc).__name__}: {exc}"
            pending.append(path)
            continue
        report.files += 1
        report.lines += lines
        report.invalid += invalid
        if fresh:
            report.counted += sum(counts.values())
        else:
            report.already += 1
        path.unlink()
    for path in pending:
        try:
            age = clock - path.stat().st_mtime
        except FileNotFoundError:
            continue
        if age > MAX_AGE_S:
            path.unlink(missing_ok=True)
            report.discarded.append(path.name)
    return report


def _log_report(report: CycleReport) -> None:
    extra = {
        "files": report.files,
        "lines": report.lines,
        "invalid": report.invalid,
        "counted": report.counted,
        "already_counted": report.already,
    }
    if report.discarded:
        logger.warning(
            "log bruto descartado sem somar (mais de 23 h)",
            extra={**extra, "discarded": report.discarded},
        )
    if report.error:
        logger.error("banco de métricas indisponível", extra={**extra, "error": report.error})
    else:
        logger.info("ciclo de métricas concluído", extra=extra)


@metrics_app.command("aggregate")
def aggregate_command(
    log_dir: Annotated[
        Path, typer.Option(help="Diretório do log de acesso do Caddy (volume caddy_logs).")
    ] = Path("/var/log/caddy"),
    every: Annotated[
        int, typer.Option(min=0, help="Repetir a cada N segundos; 0 roda um ciclo e sai.")
    ] = 0,
) -> None:
    """Soma o log de acesso rodado no banco odb_metrics e apaga os arquivos somados."""
    settings = load_settings()
    configure_logging(settings.log_level)
    engine = metrics_engine(settings, "writer")
    if engine is None:
        typer.echo("ODB_METRICS_WRITER_PASSWORD vazio: coleta desligada.", err=True)
        raise typer.Exit(code=2)
    if not log_dir.is_dir():
        typer.echo(f"diretório do log inexistente: {log_dir}", err=True)
        raise typer.Exit(code=2)
    writer = MetricsWriter(engine)
    stop = threading.Event()

    def _stop(_signum: int, _frame: FrameType | None) -> None:
        stop.set()

    # Como processo 1 do contêiner, sem tratador o SIGTERM do `docker stop` seria ignorado.
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        while True:
            report = run_cycle(log_dir, writer)
            _log_report(report)
            if every == 0:
                if report.error:
                    raise typer.Exit(code=1)
                return
            if stop.wait(every):
                return
    finally:
        writer.close()
