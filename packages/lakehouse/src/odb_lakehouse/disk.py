"""Verificação de capacidade de disco antes de escritas (§25.2)."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DiskLevel(StrEnum):
    """Classificação do uso de disco."""

    OK = "ok"
    WARN = "warn"
    BLOCK = "block"


class DiskCapacityError(RuntimeError):
    """Uso de disco acima do limite de bloqueio."""


@dataclass(frozen=True, slots=True)
class DiskStatus:
    """Uso do filesystem que contém um caminho."""

    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    used_percent: float
    level: DiskLevel


def disk_status(path: str | os.PathLike[str], warn_percent: int, block_percent: int) -> DiskStatus:
    """Mede o filesystem de ``path``, ou do ancestral existente mais próximo."""
    probe = Path(path)
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    usage = shutil.disk_usage(probe)
    used_percent = 100.0 * usage.used / usage.total if usage.total else 100.0
    if used_percent >= block_percent:
        level = DiskLevel.BLOCK
    elif used_percent >= warn_percent:
        level = DiskLevel.WARN
    else:
        level = DiskLevel.OK
    return DiskStatus(
        path=str(probe),
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
        used_percent=round(used_percent, 2),
        level=level,
    )


def ensure_capacity(
    path: str | os.PathLike[str], warn_percent: int, block_percent: int
) -> DiskStatus:
    """Lança ``DiskCapacityError`` se o uso estiver no nível de bloqueio."""
    status = disk_status(path, warn_percent, block_percent)
    if status.level is DiskLevel.BLOCK:
        msg = (
            f"uso de disco {status.used_percent}% em {status.path} "
            f">= limite de bloqueio {block_percent}%"
        )
        raise DiskCapacityError(msg)
    return status
