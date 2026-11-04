"""Catálogo semântico versionado (``configs/indicators/<escopo>.toml``).

Define, sem depender de nenhuma fonte específica:

* **classificações** e a hierarquia curada das categorias. Cada partição é um
  conjunto de categorias filhas do Total, exaustivo ou não;
* **fatos temáticos**: dataset de origem, granularidade e colunas de categoria;
* **indicadores**: posição na árvore temática, unidade, aditividade, conceito
  e incompatibilidades;
* **marcações de notas oficiais** (por exemplo, municípios com instalação
  prevista).

As validações aqui são estruturais (referências internas e unicidade). A
conferência contra os dados (unidade publicada, categorias existentes) é feita
na construção da Gold.
"""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

INDICATOR_ID = r"^[a-z][a-z0-9_]{0,63}$"
TABLE_ID = r"^(fact|dim|bridge)_[a-z0-9_]{1,60}$"
COLUMN_ID = r"^[a-z][a-z0-9_]{0,62}$"
CLASSIFICATION_ID = r"^[a-z][a-z0-9]{0,15}$"
CATEGORY_ID = r"^[0-9A-Za-z_\-]{1,32}$"
Additivity = Literal["additive", "non_additive"]


class SemanticConfigError(ValueError):
    """Catálogo semântico inválido ou inconsistente."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Partition(_Strict):
    """Conjunto de categorias filhas de uma categoria (por padrão, o Total).

    ``parent`` permite hierarquias com vários níveis, por exemplo Total →
    grupos de idade → idades simples → meses.
    """

    id: str = Field(pattern=COLUMN_ID)
    label: str
    categories: tuple[str, ...] = Field(min_length=1)
    exhaustive: bool
    parent: str | None = Field(default=None, pattern=CATEGORY_ID)
    note: str | None = None


class Classification(_Strict):
    """Dimensão de desagregação (sexo, cor ou raça, localização...)."""

    id: str = Field(pattern=CLASSIFICATION_ID)
    name: str
    # Nome da dimensão como aparece nas observações Silver.
    silver_dimension: str
    total: str = Field(pattern=CATEGORY_ID)
    partitions: tuple[Partition, ...] = ()

    @model_validator(mode="after")
    def _categories(self) -> Classification:
        seen: set[str] = set()
        ids: set[str] = set()
        for p in self.partitions:
            if p.id in ids:
                msg = f"{self.id}: partição repetida {p.id}"
                raise ValueError(msg)
            ids.add(p.id)
            for c in p.categories:
                if c == self.total:
                    msg = f"{self.id}: o Total ({c}) não pode ser filho de si mesmo"
                    raise ValueError(msg)
                if c in seen:
                    msg = f"{self.id}: categoria {c} em mais de uma partição"
                    raise ValueError(msg)
                seen.add(c)
        for p in self.partitions:
            if p.parent is not None and p.parent != self.total and p.parent not in seen:
                msg = f"{self.id}: partição {p.id} com pai {p.parent} não declarado"
                raise ValueError(msg)
        for c in seen:
            self.depth(c)  # detecta ciclos
        return self

    def parent_of(self, partition: Partition) -> str:
        """Categoria-pai de uma partição (o Total quando não declarada)."""
        return partition.parent or self.total

    def depth(self, category_id: str) -> int:
        """Profundidade na hierarquia (Total = 0)."""
        depth = 0
        current = category_id
        while current != self.total:
            partition = self.partition_of(current)
            if partition is None:
                msg = f"{self.id}: categoria {current} sem partição"
                raise ValueError(msg)
            current = self.parent_of(partition)
            depth += 1
            if depth > len(self.partitions) + 1:
                msg = f"{self.id}: ciclo na hierarquia de categorias ({category_id})"
                raise ValueError(msg)
        return depth

    def ordered(self) -> list[str]:
        """Categorias em ordem hierárquica (pai antes dos filhos, ordem declarada)."""
        out: list[str] = []

        def visit(category: str) -> None:
            out.append(category)
            for p in self.partitions:
                if self.parent_of(p) == category:
                    for child in p.categories:
                        visit(child)

        visit(self.total)
        return out

    def partition_of(self, category_id: str) -> Partition | None:
        """Partição de uma categoria (``None`` para o Total ou categoria não declarada)."""
        return next((p for p in self.partitions if category_id in p.categories), None)

    def declared(self) -> frozenset[str]:
        """Categorias declaradas, inclusive o Total."""
        return frozenset({self.total, *(c for p in self.partitions for c in p.categories)})


class FactConfig(_Strict):
    """Fato temático da Gold."""

    id: str = Field(pattern=TABLE_ID)
    dataset: str
    grain: str
    description: str
    # Classificação → coluna de chave de categoria no fato.
    classifications: dict[str, str] = Field(default_factory=dict)


class Incompatibility(_Strict):
    """Par de indicadores que não pode ser combinado numa consulta."""

    indicator: str = Field(pattern=INDICATOR_ID)
    reason: str


class IndicatorConfig(_Strict):
    """Indicador do catálogo."""

    id: str = Field(pattern=INDICATOR_ID)
    name: str
    description: str
    dataset: str
    variable: str
    fact: str = Field(pattern=TABLE_ID)
    column: str = Field(pattern=COLUMN_ID)
    unit: str
    additivity: Additivity
    concept: str = Field(pattern=INDICATOR_ID)
    path: tuple[str, ...] = Field(min_length=1)
    caveats: tuple[str, ...] = ()
    incompatible_with: tuple[Incompatibility, ...] = ()


class PendingInstallation(_Strict):
    """Municípios com instalação prevista, segundo nota oficial."""

    dataset: str
    period: str
    # Pares (nome, sigla da UF), resolvidos para códigos na construção.
    municipalities: tuple[tuple[str, str], ...] = Field(min_length=1)
    source: str


class SemanticCatalog(_Strict):
    """Catálogo de um escopo de publicação."""

    config_version: str
    scope: str = Field(pattern=INDICATOR_ID)
    classifications: tuple[Classification, ...] = ()
    facts: tuple[FactConfig, ...] = Field(min_length=1)
    indicators: tuple[IndicatorConfig, ...] = Field(min_length=1)
    pending_installation: tuple[PendingInstallation, ...] = ()
    # Hash do arquivo de origem, para a impressão digital da construção.
    content_sha256: str = ""

    @model_validator(mode="after")
    def _references(self) -> SemanticCatalog:  # noqa: PLR0912 - verificações independentes
        problems: list[str] = []
        for kind, ids in (
            ("classificação", [c.id for c in self.classifications]),
            ("fato", [f.id for f in self.facts]),
            ("indicador", [i.id for i in self.indicators]),
        ):
            repeated = sorted({i for i in ids if ids.count(i) > 1})
            if repeated:
                problems.append(f"{kind} repetido: {repeated}")
        classes = {c.id for c in self.classifications}
        facts = {f.id: f for f in self.facts}
        indicators = {i.id for i in self.indicators}
        columns: dict[str, set[str]] = {f.id: set(f.classifications.values()) for f in self.facts}
        for fact in self.facts:
            unknown = sorted(set(fact.classifications) - classes)
            if unknown:
                problems.append(f"{fact.id}: classificações não declaradas {unknown}")
        for ind in self.indicators:
            fact_cfg = facts.get(ind.fact)
            if fact_cfg is None:
                problems.append(f"{ind.id}: fato inexistente {ind.fact}")
                continue
            if fact_cfg.dataset != ind.dataset:
                problems.append(
                    f"{ind.id}: dataset {ind.dataset} difere do fato {ind.fact} "
                    f"({fact_cfg.dataset})"
                )
            if ind.column in columns[ind.fact]:
                problems.append(f"{ind.id}: coluna {ind.column} repetida em {ind.fact}")
            columns[ind.fact].add(ind.column)
            for inc in ind.incompatible_with:
                if inc.indicator not in indicators or inc.indicator == ind.id:
                    problems.append(f"{ind.id}: incompatibilidade inválida com {inc.indicator}")
        variables = [(i.dataset, i.variable) for i in self.indicators]
        repeated_vars = sorted({v for v in variables if variables.count(v) > 1})
        if repeated_vars:
            problems.append(f"variável usada por mais de um indicador: {repeated_vars}")
        for fact_id, fact in facts.items():
            if not any(i.fact == fact_id for i in self.indicators):
                problems.append(f"{fact.id}: fato sem indicadores")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def classification(self, classification_id: str) -> Classification:
        """Classificação por identificador."""
        for c in self.classifications:
            if c.id == classification_id:
                return c
        msg = f"classificação inexistente: {classification_id}"
        raise SemanticConfigError(msg)

    def fact(self, fact_id: str) -> FactConfig:
        """Fato por identificador."""
        for f in self.facts:
            if f.id == fact_id:
                return f
        msg = f"fato inexistente: {fact_id}"
        raise SemanticConfigError(msg)

    def indicators_of(self, fact_id: str) -> list[IndicatorConfig]:
        """Indicadores (medidas) de um fato, na ordem do arquivo."""
        return [i for i in self.indicators if i.fact == fact_id]

    def datasets(self) -> list[str]:
        """Datasets usados pelo catálogo, sem repetição e na ordem dos fatos."""
        return list(dict.fromkeys(f.dataset for f in self.facts))

    def incompatibilities(self) -> dict[frozenset[str], str]:
        """Pares incompatíveis (simétricos) e o motivo."""
        return {
            frozenset({i.id, inc.indicator}): inc.reason
            for i in self.indicators
            for inc in i.incompatible_with
        }


def load_catalog(path: Path) -> SemanticCatalog:
    """Lê e valida um arquivo de catálogo semântico."""
    content = path.read_bytes()
    try:
        data = tomllib.loads(content.decode("utf-8"))
        return SemanticCatalog.model_validate(
            {**data, "content_sha256": hashlib.sha256(content).hexdigest()}
        )
    except (tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"{path}: catálogo semântico inválido: {exc}"
        raise SemanticConfigError(msg) from exc


def load_scope(config_dir: str | Path, scope: str) -> SemanticCatalog:
    """Catálogo do escopo informado (``<dir>/<escopo>.toml``)."""
    path = Path(config_dir) / f"{scope}.toml"
    if not path.is_file():
        msg = f"catálogo semântico do escopo {scope!r} não encontrado em {path}"
        raise SemanticConfigError(msg)
    catalog = load_catalog(path)
    if catalog.scope != scope:
        msg = f"{path}: escopo declarado {catalog.scope!r} difere do nome do arquivo"
        raise SemanticConfigError(msg)
    return catalog
