"""Navegação e exposição do portal (``configs/portal/<escopo>.toml``, ADR-0009).

Tema > subtema > KPI. Cada KPI aponta para um indicador da Gold e lista as
dimensões (classificação e partição de categorias) liberadas no portal. A
configuração é conferida contra o release ativo: indicador publicado,
classificação do indicador e partição existente.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

_ID = r"^[a-z][a-z0-9_]{0,63}$"


class PortalConfigError(ValueError):
    """Configuração do portal inválida ou incoerente com o release."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DimensionConfig(_Strict):
    """Classificação exposta e a partição de categorias mostrada."""

    classification: str = Field(pattern=r"^c\d+$")
    partition: str = Field(pattern=_ID)
    label: str


class KpiConfig(_Strict):
    """KPI do portal: um indicador da Gold e suas dimensões expostas."""

    id: str = Field(pattern=_ID)
    label: str
    indicator: str = Field(pattern=_ID)
    dimensions: tuple[DimensionConfig, ...] = ()


class SubthemeConfig(_Strict):
    """Subtema."""

    id: str = Field(pattern=_ID)
    label: str
    kpis: tuple[KpiConfig, ...] = Field(min_length=1)


class ThemeConfig(_Strict):
    """Tema."""

    id: str = Field(pattern=_ID)
    label: str
    subthemes: tuple[SubthemeConfig, ...] = Field(min_length=1)


class PortalConfig(_Strict):
    """Configuração de um escopo."""

    config_version: str
    scope: str = Field(pattern=_ID)
    dimension_order: tuple[str, ...] = ()
    themes: tuple[ThemeConfig, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _structure(self) -> PortalConfig:
        problems: list[str] = []
        kpis = [k.id for k in self.kpis()]
        repeated = sorted({k for k in kpis if kpis.count(k) > 1})
        if repeated:
            problems.append(f"KPI repetido: {repeated}")
        for kpi in self.kpis():
            dims = [d.classification for d in kpi.dimensions]
            unknown = [d for d in dims if d not in self.dimension_order]
            if unknown:
                problems.append(f"{kpi.id}: dimensões fora de dimension_order: {unknown}")
            elif dims != sorted(dims, key=self.dimension_order.index):
                problems.append(f"{kpi.id}: dimensões fora da ordem {list(self.dimension_order)}")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def kpis(self) -> list[KpiConfig]:
        """Todos os KPIs, na ordem do arquivo."""
        return [k for t in self.themes for s in t.subthemes for k in s.kpis]

    def kpi(self, kpi_id: str) -> KpiConfig | None:
        """KPI por identificador."""
        return next((k for k in self.kpis() if k.id == kpi_id), None)


def load_portal(config_dir: str | Path, scope: str) -> PortalConfig:
    """Carrega ``<config_dir>/<scope>.toml``."""
    path = Path(config_dir) / f"{scope}.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        config = PortalConfig.model_validate(data)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"{path}: configuração do portal inválida: {exc}"
        raise PortalConfigError(msg) from exc
    if config.scope != scope:
        msg = f"{path}: escopo {config.scope!r} difere do esperado {scope!r}"
        raise PortalConfigError(msg)
    return config


def check_against_release(
    config: PortalConfig,
    indicators: Mapping[str, Mapping[str, Any]],
    partitions: Mapping[str, Sequence[str]],
) -> None:
    """Confere a configuração contra o release (``dim_indicator`` e ``dim_category``).

    ``partitions`` mapeia classificação → partições publicadas.
    """
    problems: list[str] = []
    for kpi in config.kpis():
        meta = indicators.get(kpi.indicator)
        if meta is None:
            problems.append(f"{kpi.id}: indicador {kpi.indicator} não publicado no release")
            continue
        classes = set(meta.get("classification_ids") or ())
        for dim in kpi.dimensions:
            if dim.classification not in classes:
                problems.append(
                    f"{kpi.id}: {kpi.indicator} não tem a classificação {dim.classification}"
                )
            elif dim.partition not in partitions.get(dim.classification, ()):
                problems.append(
                    f"{kpi.id}: partição {dim.partition} inexistente em {dim.classification}"
                )
    if problems:
        raise PortalConfigError("; ".join(problems))
