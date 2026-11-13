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


class SeriesConfig(_Strict):
    """Série composta declarada (ADR-0022): datasets de fontes ou tabelas distintas.

    Diferente de ``silver.series`` (o dataset diz a que série pertence), aqui a série
    lista os membros, e um dataset pode servir o próprio indicador e várias séries
    compostas. A ordem da lista é a ``series_order`` (o último é o mais recente).
    """

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,99}$")
    members: tuple[str, ...] = Field(min_length=2)
    title: str
    description: str = ""


class SourcesFile(_Strict):
    """Conteúdo de um arquivo de configuração de fontes."""

    config_version: str
    # Sem instituição, o arquivo é um fragmento: só acrescenta datasets a
    # fontes e licenças declaradas em outro arquivo (por exemplo, os datasets
    # gerados por `odb panorama gerar`).
    institution: InstitutionConfig | None = None
    licenses: tuple[LicenseConfig, ...] = ()
    sources: tuple[SourceConfig, ...] = ()
    datasets: tuple[DatasetConfig, ...] = ()
    series: tuple[SeriesConfig, ...] = ()

    @model_validator(mode="after")
    def _fragment(self) -> SourcesFile:
        if self.institution is None and (self.licenses or self.sources):
            msg = "um fragmento sem instituição só pode declarar datasets"
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
        self.series: dict[str, SeriesConfig] = {}
        for f in self.files:
            if f.institution is not None:
                self._add(self.institutions, f.institution.id, f.institution, "instituição")
                for src in f.sources:
                    self.source_institution[src.id] = f.institution.id
            for lic in f.licenses:
                self._add(self.licenses, lic.id, lic, "licença")
            for src in f.sources:
                self._add(self.sources, src.id, src, "fonte")
            for ds in f.datasets:
                self._add(self.datasets, ds.id, ds, "dataset")
            for ser in f.series:
                self._add(self.series, ser.id, ser, "série")
        for ds in self.datasets.values():
            if ds.source not in self.sources:
                msg = f"dataset {ds.id}: fonte desconhecida {ds.source!r}"
                raise ConfigError(msg)
            if ds.license not in self.licenses:
                msg = f"dataset {ds.id}: licença desconhecida {ds.license!r}"
                raise ConfigError(msg)
        for ser in self.series.values():
            unknown = [m for m in ser.members if m not in self.datasets]
            if unknown or ser.id in self.datasets:
                msg = f"série {ser.id}: membros desconhecidos {unknown} ou id de dataset"
                raise ConfigError(msg)

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

    def series_of(self, series_id: str) -> list[str]:
        """Membros de uma série, em ordem (o último é o mais recente); vazio se não for.

        Vale para as duas formas: a série composta declarada (``[[series]]``,
        ADR-0022) e a série por ``silver.series`` + ``series_order`` (ADR-0016).
        """
        if series_id in self.series:
            return list(self.series[series_id].members)
        members = [d for d in self.datasets.values() if d.silver.get("series") == series_id]
        members.sort(key=lambda d: (int(d.silver.get("series_order", 0)), d.id))
        return [d.id for d in members]

    def series_order(self, series_id: str, dataset_id: str) -> int:
        """Posição do membro na série (1, 2, ...)."""
        return self.series_of(series_id).index(dataset_id) + 1

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
