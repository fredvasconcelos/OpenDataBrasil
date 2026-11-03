"""Armazenamento Bronze imutável (§6.4, §6.5).

Organização física::

    bronze/<source_id>/<dataset_id>/<AAAAMMDDtHHMMSSz>-<ingestion8>/<artefato>
    bronze/<source_id>/<dataset_id>/quarantine/<AAAAMMDDtHHMMSSz>-<ingestion8>/<artefato>

* os nomes de artefato são definidos pela plataforma, e a URL original fica nos
  metadados;
* arquivos são criados de forma exclusiva, nunca sobrescritos, verificados por
  SHA-256 após a cópia e marcados como somente leitura;
* downloads ficam primeiro em ``tmp/ingestion/<ingestion_id>``, e o Bronze só
  recebe arquivos completos;
* a deduplicação (mesmo checksum) é decidida pelo runner com o registro do
  catálogo: nesse caso, nenhum byte novo é gravado.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from datetime import datetime
from pathlib import Path

from odb_common.storage import LakehouseLayout, Layer, uri_to_local_path

QUARANTINE_DIR = "quarantine"
_READ_ONLY = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH


class BronzeIntegrityError(RuntimeError):
    """Arquivo gravado não confere com o checksum esperado."""


def sha256_file(path: Path) -> str:
    """SHA-256 de um arquivo, lido em blocos."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot_segment(started_at: datetime, ingestion_id: str) -> str:
    """Segmento de diretório da ingestão: instante UTC + prefixo do identificador."""
    return f"{started_at.strftime('%Y%m%dt%H%M%Sz')}-{ingestion_id.replace('-', '')[:8]}"


class BronzeStore:
    """Grava artefatos completos e verificados na camada Bronze."""

    def __init__(self, layout: LakehouseLayout) -> None:
        """Associa o armazenamento ao lakehouse."""
        self._layout = layout

    @property
    def bronze_root(self) -> Path:
        """Diretório local da camada Bronze."""
        return Path(uri_to_local_path(self._layout.layer_uri(Layer.BRONZE)))

    def staging_dir(self, ingestion_id: str) -> Path:
        """Diretório temporário da ingestão (fora da Bronze)."""
        uri = self._layout.table_uri(Layer.TMP, "ingestion", ingestion_id)
        path = Path(uri_to_local_path(uri))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup_staging(self, ingestion_id: str) -> None:
        """Remove o diretório temporário da ingestão."""
        shutil.rmtree(self.staging_dir(ingestion_id), ignore_errors=True)

    def store(
        self,
        temp_path: Path,
        *,
        source_id: str,
        dataset_id: str,
        snapshot: str,
        artifact_name: str,
        expected_sha256: str,
        quarantine: bool = False,
    ) -> str:
        """Copia ``temp_path`` para a Bronze e devolve a URI do arquivo."""
        dirs = [source_id, dataset_id, *([QUARANTINE_DIR] if quarantine else []), snapshot]
        uri = self._layout.object_uri(Layer.BRONZE, *dirs, filename=artifact_name)
        target = Path(uri_to_local_path(uri))
        target.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("rb") as src, target.open("xb") as dst:  # nunca sobrescreve
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        if sha256_file(target) != expected_sha256:
            target.chmod(stat.S_IRUSR | stat.S_IWUSR)
            target.unlink()
            msg = f"checksum divergente após cópia para {uri}"
            raise BronzeIntegrityError(msg)
        target.chmod(_READ_ONLY)
        return uri

    def remove_unregistered(self, uri: str) -> None:
        """Remove um arquivo recém-gravado que não chegou a ser registrado.

        Uso exclusivo do runner, quando o registro no catálogo falha (por
        exemplo, por corrida de deduplicação). Nunca use para artefatos registrados.
        """
        path = Path(uri_to_local_path(uri))
        if path.exists():
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            path.unlink()

    def verify(self, uri: str, expected_sha256: str) -> bool:
        """Confere a integridade de um artefato existente."""
        path = Path(uri_to_local_path(uri))
        return path.is_file() and sha256_file(path) == expected_sha256
