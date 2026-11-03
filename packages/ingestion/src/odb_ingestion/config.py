"""Configuração versionada de instituições, licenças, fontes e datasets.

Cada arquivo ``configs/sources/*.toml`` descreve uma instituição. Os parâmetros
específicos de cada conector (``[datasets.params]``) são validados pelo próprio
conector. O núcleo não conhece regras de nenhuma fonte.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID_PATTERN = r"^[a-z0-9][a-z0-9\-]{0,63}$"
AccessClassification = Literal[
    "public_authorized", "public_conditional", "requires_review", "restricted", "forbidden"
]


class ConfigError(ValueError):
    """Configuração de fontes inválida ou inconsistente."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InstitutionConfig(_Strict):
    """Instituição publicadora."""

    id: str = Field(pattern=ID_PATTERN)
    name: str
    acronym: str
    url: str


class LicenseConfig(_Strict):
    """Licença ou fundamento de reutilização (§6.2, §23)."""

    id: str = Field(pattern=ID_PATTERN)
    name: str
    url: str | None = None
    conditions: str
    review_status: Literal["approved", "requires_review"]
    notes: str | None = None


class HttpPolicy(_Strict):
    """Política de acesso HTTP de uma fonte."""

    timeout_s: float = Field(default=60.0, gt=0)
    connect_timeout_s: float = Field(default=15.0, gt=0)
    max_attempts: int = Field(default=5, ge=1, le=10)
    backoff_initial_s: float = Field(default=1.0, ge=0)
    backoff_max_s: float = Field(default=60.0, ge=0)
    max_retry_after_s: float = Field(default=300.0, ge=0)
    min_interval_s: float = Field(default=1.0, ge=0)
    max_bytes: int = Field(default=500 * 1024**2, ge=1)
    user_agent: str = "OpenDataBrasil (+https://github.com/fredvasconcelos/OpenDataBrasil)"


class SourceConfig(_Strict):
    """Sistema ou serviço de onde os dados são obtidos."""

    id: str = Field(pattern=ID_PATTERN)
    name: str
    connector: str
    base_url: str
    documentation_url: str | None = None
    http: HttpPolicy = HttpPolicy()


class DatasetConfig(_Strict):
    """Dataset oficial e os parâmetros do conector que o obtém."""

    id: str = Field(pattern=ID_PATTERN)
    source: str
    official_id: str
    title: str
    description: str
    license: str
    access_classification: AccessClassification
    periodicity: str
    reference_url: str | None = None
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)
    # Parâmetros da transformação Silver (interpretados pelo pacote processing).
    silver: dict[str, Any] = Field(default_factory=dict)

    def config_sha256(self) -> str:
        """Checksum canônico da configuração, registrado no catálogo."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()


class SourcesFile(_Strict):
    """Conteúdo de um arquivo de configuração de fontes."""

    config_version: str
    institution: InstitutionConfig
    licenses: tuple[LicenseConfig, ...] = ()
    sources: tuple[SourceConfig, ...] = ()
    datasets: tuple[DatasetConfig, ...] = ()

    @model_validator(mode="after")
    def _references(self) -> SourcesFile:
        licenses = {lic.id for lic in self.licenses}
        sources = {src.id for src in self.sources}
        for ds in self.datasets:
            if ds.source not in sources:
                msg = f"dataset {ds.id}: fonte desconhecida {ds.source!r}"
                raise ValueError(msg)
            if ds.license not in licenses:
                msg = f"dataset {ds.id}: licença desconhecida {ds.license!r}"
                raise ValueError(msg)
        return self


class SourceCatalog:
    """União validada de todos os arquivos de configuração."""

    def __init__(self, files: Iterable[SourcesFile]) -> None:
        """Indexa as entidades e rejeita identificadores duplicados."""
        self.files = tuple(files)
        self.institutions: dict[str, InstitutionConfig] = {}
        self.licenses: dict[str, LicenseConfig] = {}
        self.sources: dict[str, SourceConfig] = {}
        self.datasets: dict[str, DatasetConfig] = {}
        self.source_institution: dict[str, str] = {}
        for f in self.files:
            self._add(self.institutions, f.institution.id, f.institution, "instituição")
            for lic in f.licenses:
                self._add(self.licenses, lic.id, lic, "licença")
            for src in f.sources:
                self._add(self.sources, src.id, src, "fonte")
                self.source_institution[src.id] = f.institution.id
            for ds in f.datasets:
                self._add(self.datasets, ds.id, ds, "dataset")

    @staticmethod
    def _add(index: dict[str, Any], key: str, value: Any, kind: str) -> None:
        if key in index:
            msg = f"{kind} duplicada nos arquivos de configuração: {key}"
            raise ConfigError(msg)
        index[key] = value

    def dataset(self, dataset_id: str) -> DatasetConfig:
        """Dataset por identificador."""
        try:
            return self.datasets[dataset_id]
        except KeyError as exc:
            msg = f"dataset não configurado: {dataset_id}"
            raise ConfigError(msg) from exc

    def datasets_of(self, source_id: str) -> list[DatasetConfig]:
        """Datasets de uma fonte, na ordem de declaração."""
        return [d for d in self.datasets.values() if d.source == source_id]


def load_sources(config_dir: str | Path) -> SourceCatalog:
    """Lê e valida todos os ``*.toml`` do diretório."""
    directory = Path(config_dir)
    paths = sorted(directory.glob("*.toml"))
    if not paths:
        msg = f"nenhum arquivo de fontes em {directory}"
        raise ConfigError(msg)
    files = []
    for path in paths:
        try:
            files.append(SourcesFile.model_validate(tomllib.loads(path.read_text("utf-8"))))
        except (tomllib.TOMLDecodeError, ValueError) as exc:
            msg = f"{path.name}: {exc}"
            raise ConfigError(msg) from exc
    return SourceCatalog(files)
