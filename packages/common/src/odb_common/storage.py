"""Resolução de URIs de armazenamento do lakehouse.

Nenhum outro módulo deve montar caminhos físicos por conta própria. Tudo passa
por ``LakehouseLayout``, o que centraliza a futura troca de ``file://`` por
armazenamento em nuvem (§26.1).

Os segmentos de caminho são validados para impedir path traversal e nomes
ambíguos. Essa camada nunca recebe caminhos fornecidos por usuários finais.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

SUPPORTED_SCHEMES = frozenset({"file"})
_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,127}$")
# Nome de arquivo definido pela plataforma (nunca o nome fornecido pela fonte).
_FILENAME = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,100}(\.[a-z0-9]{1,10}){0,2}$")


class StorageError(ValueError):
    """URI ou segmento de caminho inválido."""


class Layer(StrEnum):
    """Camadas físicas do lakehouse."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    TMP = "tmp"


def validate_segment(segment: str) -> str:
    """Garante que o segmento é minúsculo, sem separadores e sem ``..``."""
    if not _SEGMENT.fullmatch(segment):
        msg = f"segmento de caminho inválido: {segment!r}"
        raise StorageError(msg)
    return segment


def validate_filename(name: str) -> str:
    """Garante nome de arquivo minúsculo, com no máximo duas extensões e sem separadores."""
    if not _FILENAME.fullmatch(name):
        msg = f"nome de arquivo inválido: {name!r}"
        raise StorageError(msg)
    return name


def uri_to_local_path(uri: str) -> PurePosixPath:
    """Converte uma URI ``file://`` absoluta em caminho POSIX."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        msg = f"apenas URIs file:// podem ser convertidas em caminho local: {uri!r}"
        raise StorageError(msg)
    if parsed.netloc not in ("", "localhost"):
        msg = f"URI file:// com host não suportada: {uri!r}"
        raise StorageError(msg)
    path = PurePosixPath(unquote(parsed.path))
    if not path.is_absolute() or ".." in path.parts:
        msg = f"URI file:// deve ser absoluta e normalizada: {uri!r}"
        raise StorageError(msg)
    return path


@dataclass(frozen=True, slots=True)
class LakehouseLayout:
    """Organização física das camadas a partir de uma URI raiz."""

    root_uri: str

    def __post_init__(self) -> None:
        """Valida o esquema e normaliza a URI raiz (sem barra final)."""
        scheme = urlparse(self.root_uri).scheme
        if scheme not in SUPPORTED_SCHEMES:
            msg = f"esquema de armazenamento não suportado: {scheme!r}"
            raise StorageError(msg)
        uri_to_local_path(self.root_uri)
        object.__setattr__(self, "root_uri", self.root_uri.rstrip("/"))

    def layer_uri(self, layer: Layer) -> str:
        """URI raiz de uma camada."""
        return f"{self.root_uri}/{layer.value}"

    def table_uri(self, layer: Layer, *segments: str) -> str:
        """URI de uma tabela ou artefato. Exige ao menos um segmento validado."""
        if not segments:
            msg = "ao menos um segmento é obrigatório"
            raise StorageError(msg)
        clean = "/".join(validate_segment(s) for s in segments)
        return f"{self.layer_uri(layer)}/{clean}"

    def object_uri(self, layer: Layer, *segments: str, filename: str) -> str:
        """URI de um arquivo (por exemplo, um artefato Bronze) dentro de diretórios validados."""
        return f"{self.table_uri(layer, *segments)}/{validate_filename(filename)}"

    def layer_of(self, uri: str) -> Layer:
        """Identifica a camada de uma URI pertencente a este lakehouse."""
        prefix = self.root_uri + "/"
        if not uri.startswith(prefix):
            msg = f"URI fora do lakehouse: {uri!r}"
            raise StorageError(msg)
        head = uri[len(prefix) :].split("/", 1)[0]
        try:
            return Layer(head)
        except ValueError as exc:
            msg = f"URI não pertence a uma camada conhecida: {uri!r}"
            raise StorageError(msg) from exc
