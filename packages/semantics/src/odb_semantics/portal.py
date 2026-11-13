"""Navegação e exposição do portal (``configs/portal/<escopo>.toml``, ADR-0009).

Tema > subtema > KPI. Cada KPI aponta para um indicador da Gold e lista as
dimensões (classificação e partição de categorias) liberadas no portal. A
configuração é conferida contra um release (ADR-0015): indicador publicado,
classificação do indicador, partição existente e, com o panorama, a mesma
tabela de origem. A conferência vale nos dois lados: rígida no worker, antes de
ativar o release, e tolerante na API, que esconde só os KPIs com problema.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from odb_semantics.panorama import resolve_links

if TYPE_CHECKING:
    from odb_semantics.panorama import Panorama

_ID = r"^[a-z][a-z0-9_]{0,63}$"


# Unidades de quantidade (contagens e totais): as categorias somam o Total do território,
# e o % de cada uma faz sentido mesmo quando a fonte não deixa somar entre territórios
# (estimativas da PNAD, por exemplo). Taxas, médias, índices e valores per capita
# ("%", "Reais" médios, "Anos", "Quilogramas" per capita) ficam de fora.
QUANTITY_UNITS = frozenset(
    {
        "Pessoas",
        "Mil pessoas",
        "Unidades",
        "Mil unidades",
        "Domicílios",
        "Famílias",
        "Estabelecimentos",
        "Empresas",
        "Cabeças",
        "Hectares",
        "Mil hectares",
        "Toneladas",
        "Mil toneladas",
        "Mil Reais",
        "Milhões de Reais",
        "Mil dúzias",
        "Mil litros",
        "Vítimas",
        "Óbitos",
    }
)


def allows_category_shares(unit: str, additivity: str) -> bool:
    """O % de cada categoria sobre o Total vale para este indicador? (DS 2.3.12)."""
    return additivity == "additive" or unit.strip() in QUANTITY_UNITS


class PortalConfigError(ValueError):
    """Configuração do portal inválida ou incoerente com o release."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DimensionConfig(_Strict):
    """Classificação exposta e a partição de categorias mostrada."""

    # Mesmo padrão do catálogo semântico: "c86" (SIDRA) ou próprias, como "sexosim".
    classification: str = Field(pattern=r"^[a-z][a-z0-9]{0,15}$")
    partition: str = Field(pattern=_ID)
    label: str


class CorrectionConfig(_Strict):
    """Correção de valores em moeda por um índice de preços (ADR-0020).

    O fator de um período é o acumulado do índice entre o mês de referência dele e o do
    período mais recente do KPI (que avança sozinho com dados novos):
    fator = Π(1 + v_m/100) dos meses depois da referência do período até a do mais recente.
    Com ``dimension`` e ``groups``, cada categoria usa o grupo do índice correspondente
    (ex.: alimentação → Alimentação e bebidas); as demais, o índice geral.
    """

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str
    # Indicador da Gold com a variação mensal do índice (% ao mês), por grupo (c315).
    indicator: str = Field(pattern=_ID)
    group_classification: str = Field(default="c315", pattern=r"^[a-z][a-z0-9]{0,15}$")
    general: str = Field(default="7169", pattern=r"^\d+$")  # índice geral
    # Como achar o índice de cada período do KPI:
    # - "months": um mês de referência por período, em ``reference_months`` (pesquisas
    #   com data de referência própria, como a POF: "2018" → "2018M01");
    # - "period": o próprio período. Mês: o índice do mês; trimestre, semestre e ano: a
    #   média do índice nos meses do período (valores que são fluxos ou médias do
    #   período, como o PIB anual ou o custo médio do m² no ano).
    reference: Literal["months", "period"] = "months"
    reference_months: dict[str, str] = Field(default_factory=dict)
    # Classificação do KPI cujas categorias têm grupo próprio, e categoria → grupo.
    dimension: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9]{0,15}$")
    groups: dict[str, str] = Field(default_factory=dict)
    note: str = ""

    @model_validator(mode="after")
    def _reference_months(self) -> CorrectionConfig:
        if self.reference == "months" and not self.reference_months:
            msg = f"correção {self.id}: reference = 'months' exige reference_months"
            raise ValueError(msg)
        return self


class KpiConfig(_Strict):
    """KPI do portal: um indicador da Gold e suas dimensões expostas."""

    id: str = Field(pattern=_ID)
    label: str
    indicator: str = Field(pattern=_ID)
    dimensions: tuple[DimensionConfig, ...] = ()
    # Categoria da primeira dimensão cuja participação no Total colore o mapa (em %).
    # Para KPIs cujo Total é só o universo (ex.: % de municípios com Plano Diretor).
    map_share: str | None = Field(default=None, pattern=r"^[0-9A-Za-z_\-]{1,32}$")
    # Dimensões marginais (ADR-0016): cada uma vem com as demais no Total, sem os
    # cruzamentos. O portal detalha uma por vez, e a API recusa duas juntas.
    exclusive_dimensions: bool = False
    # Cruzamentos completos (C1): grupos de dimensões que se cruzam, só nos níveis de
    # ``crossed_levels`` (Brasil, região, UF). Nos demais, continua uma por vez.
    crossed: tuple[tuple[str, ...], ...] = ()
    crossed_levels: tuple[str, ...] = ()

    def can_cross(self, dims: Sequence[str], level: str | None) -> bool:
        """As dimensões pedidas se cruzam nesse nível?"""
        return level in self.crossed_levels and any(set(dims) <= set(g) for g in self.crossed)

    # Níveis com mapa, se diferentes dos que têm geometria. Vazio: sem mapa (POF de
    # 1987 e 1995: só Brasília e Goiânia teriam cor na malha municipal, ADR-0016).
    map_levels: tuple[str, ...] | None = None
    # Correções de valores em moeda por índice de preços (ADR-0020): "Corrigir por".
    corrections: tuple[CorrectionConfig, ...] = ()

    @model_validator(mode="after")
    def _share(self) -> KpiConfig:
        if self.map_share is not None and not self.dimensions:
            msg = f"{self.id}: map_share exige ao menos uma dimensão"
            raise ValueError(msg)
        if self.exclusive_dimensions and len(self.dimensions) < 2:  # noqa: PLR2004
            msg = f"{self.id}: exclusive_dimensions exige duas dimensões ou mais"
            raise ValueError(msg)
        return self


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


def merge_themes(
    themes: Sequence[Mapping[str, Any]], extra: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Acrescenta temas de um fragmento: mesmo ``id`` junta subtemas e KPIs."""
    merged = [
        {**t, "subthemes": [{**s, "kpis": list(s["kpis"])} for s in t["subthemes"]]} for t in themes
    ]
    for theme in extra:
        target = next((t for t in merged if t["id"] == theme["id"]), None)
        if target is None:
            merged.append(
                {**theme, "subthemes": [{**s, "kpis": list(s["kpis"])} for s in theme["subthemes"]]}
            )
            continue
        for sub in theme["subthemes"]:
            same = next((s for s in target["subthemes"] if s["id"] == sub["id"]), None)
            if same is None:
                target["subthemes"].append({**sub, "kpis": list(sub["kpis"])})
            else:
                same["kpis"].extend(sub["kpis"])
    return merged


def load_portal(config_dir: str | Path, scope: str) -> PortalConfig:
    """Carrega ``<config_dir>/<scope>.toml`` e os fragmentos ``<config_dir>/<scope>/*.toml``.

    Um fragmento (por exemplo, os KPIs gerados por ``odb panorama gerar``)
    declara o mesmo ``scope`` e só acrescenta ``themes``.
    """
    path = Path(config_dir) / f"{scope}.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for fragment in sorted((Path(config_dir) / scope).glob("*.toml")):
            extra = tomllib.loads(fragment.read_text(encoding="utf-8"))
            unknown = sorted(set(extra) - {"config_version", "scope", "themes", "dimension_order"})
            if extra.get("scope") != scope or unknown:
                msg = f"{fragment}: fragmento do portal inválido (escopo ou chaves {unknown})"
                raise PortalConfigError(msg)
            data["themes"] = merge_themes(data.get("themes", []), extra.get("themes", []))
            # Classificações novas entram no fim da ordem de aninhamento do tooltip.
            order = list(data.get("dimension_order", []))
            order += [c for c in extra.get("dimension_order", []) if c not in order]
            data["dimension_order"] = order
        config = PortalConfig.model_validate(data)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"{path}: configuração do portal inválida: {exc}"
        raise PortalConfigError(msg) from exc
    if config.scope != scope:
        msg = f"{path}: escopo {config.scope!r} difere do esperado {scope!r}"
        raise PortalConfigError(msg)
    return config


def release_problems(
    config: PortalConfig,
    indicators: Mapping[str, Mapping[str, Any]],
    partitions: Mapping[str, Sequence[str]],
    panorama: Panorama | None = None,
) -> dict[str, list[str]]:
    """Problemas de cada KPI contra o release (``dim_indicator`` e ``dim_category``).

    ``partitions`` mapeia classificação → partições publicadas. Com o
    ``panorama``, confere também se a tabela de origem publicada é a que o item
    declara. Devolve só os KPIs com problema, na ordem da configuração.
    """
    problems: dict[str, list[str]] = {}
    for kpi in config.kpis():
        meta = indicators.get(kpi.indicator)
        if meta is None:
            problems[kpi.id] = [f"indicador {kpi.indicator} não publicado no release"]
            continue
        classes = set(meta.get("classification_ids") or ())
        for dim in kpi.dimensions:
            if dim.classification not in classes:
                problem = f"{kpi.indicator} não tem a classificação {dim.classification}"
            elif dim.partition not in partitions.get(dim.classification, ()):
                problem = f"partição {dim.partition} inexistente em {dim.classification}"
            else:
                continue
            problems.setdefault(kpi.id, []).append(problem)
    for kpi_id, missing in _correction_problems(config, indicators).items():
        problems.setdefault(kpi_id, []).extend(missing)
    if panorama is not None:
        links = resolve_links(panorama, (k.id for k in config.kpis()))
        for _, _, item in panorama.items():
            linked = config.kpi(links[item.id] or "")
            if linked is None or linked.indicator not in indicators:
                continue  # planejado, ou indicador ausente (já registrado)
            published = str(indicators[linked.indicator].get("source_table_id"))
            if published != item.tabela:
                problems.setdefault(linked.id, []).append(
                    f"tabela {item.tabela} no panorama ({item.id}), {published} na Gold"
                )
    return problems


def _correction_problems(
    config: PortalConfig, indicators: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[str]]:
    """Correções cujo índice de preços não está no release (ADR-0020)."""
    out: dict[str, list[str]] = {}
    for kpi in config.kpis():
        for corr in kpi.corrections:
            if corr.indicator not in indicators:
                out.setdefault(kpi.id, []).append(
                    f"índice da correção {corr.id} ({corr.indicator}) não publicado no release"
                )
    return out


class ShortLabels(_Strict):
    """Rótulos curtos do portal (``configs/portal/rotulos.toml``, DS 2.3.11).

    O nome oficial continua na Gold e nas exportações; o portal mostra o curto e
    oferece o completo no botão de informação da tabela.
    """

    dimensoes: dict[str, str] = Field(default_factory=dict)
    categorias: dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def _origin(cid: str) -> str:
        # Classificação própria de tabela ("c653t4423", ADR-0014) → a de origem ("c653").
        return re.sub(r"t\d+$", "", cid)

    def dimension(self, cid: str) -> str | None:
        """Rótulo curto da classificação (ou da de origem); None se não houver."""
        return self.dimensoes.get(cid) or self.dimensoes.get(self._origin(cid))

    def category(self, key: str) -> str | None:
        """Rótulo curto da categoria pela chave exata; None se não houver."""
        return self.categorias.get(key)


def load_short_labels(path: str | Path) -> ShortLabels:
    """Carrega os rótulos curtos; sem o arquivo, nenhum rótulo (vale o nome oficial)."""
    path = Path(path)
    if not path.is_file():
        return ShortLabels()
    try:
        return ShortLabels.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"{path}: rótulos curtos inválidos: {exc}"
        raise PortalConfigError(msg) from exc


def describe_problems(problems: Mapping[str, Sequence[str]]) -> str:
    """Problemas em uma linha: ``kpi: problema; kpi: problema``."""
    return "; ".join(f"{kpi}: {p}" for kpi, items in problems.items() for p in items)


def check_against_release(
    config: PortalConfig,
    indicators: Mapping[str, Mapping[str, Any]],
    partitions: Mapping[str, Sequence[str]],
    panorama: Panorama | None = None,
) -> None:
    """Conferência rígida: erro se algum KPI tiver problema (ver ``release_problems``)."""
    problems = release_problems(config, indicators, partitions, panorama)
    if problems:
        raise PortalConfigError(describe_problems(problems))
