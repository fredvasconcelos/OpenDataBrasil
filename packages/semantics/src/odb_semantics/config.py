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
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from odb_semantics.geography import LEVELS_BY_ID, is_ancestor_level

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
    # False quando a fonte não permite somar as categorias (podem se sobrepor,
    # como "posse de bens"): a reconciliação com o Total não se aplica.
    summable: bool = True


class Classification(_Strict):
    """Dimensão de desagregação (sexo, cor ou raça, localização...)."""

    id: str = Field(pattern=CLASSIFICATION_ID)
    name: str
    # Nome da dimensão como aparece nas observações Silver.
    silver_dimension: str
    total: str = Field(pattern=CATEGORY_ID)
    partitions: tuple[Partition, ...] = ()
    # Datasets em que esta classificação lê a dimensão. Vazio: todos os demais. Serve a
    # fontes que usam o mesmo nome de dimensão com outros códigos: o "Sexo" do SIM
    # (1, 2, 9) e do Sinesp (masculino, feminino...) não é a c2 do IBGE (4, 5), e uma
    # classificação própria, com o mesmo rótulo no portal, lê só esses datasets.
    datasets: tuple[str, ...] = ()

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


class AggregateRule(_Strict):
    """Categoria-alvo como soma de categorias da tabela (ADR-0022).

    Ex.: "Outro tipo" (código da PNAD) = fossa rudimentar + vala + rio + outra forma
    (códigos do Censo). As categorias somadas continuam, a menos que saiam em
    ``drop_categories``.
    """

    dimension: str
    target: str = Field(pattern=r"^[0-9A-Za-z_\-]{1,32}$")
    name: str
    sources: tuple[str, ...] = Field(min_length=1)


class TableRule(_Strict):
    """Regras de uma tabela de origem de um fato em série (ADR-0016).

    Numa série de tabelas (``silver.series``), cada edição pode ter classificações
    próprias. Ex.: a POF 2002-2003 (SIDRA 2309) tem a situação do domicílio e
    outro conceito de classe de rendimento; a 2008-2009 e a 2017-2018 (1594 e
    6715) usam a c339.
    """

    # Como ``FactConfig.fixed_categories``, só para as linhas desta tabela.
    fixed_categories: dict[str, str] = Field(default_factory=dict)
    # Classificações do fato que a tabela não tem: o valor é do universo inteiro e
    # entra no Total delas (a POF 2002 não tem a c339; o valor é de todas as famílias).
    missing_as_total: tuple[str, ...] = ()
    # Dimensão da Silver com outro nome nesta tabela → nome da dimensão do fato. Ex.: as
    # classes de rendimento da POF 2002 (outro conceito, c12191) entram como "Classes de
    # rendimento" do fato, com categorias próprias.
    rename_dimensions: dict[str, str] = Field(default_factory=dict)
    # Dimensão (já renomeada) → {código nesta tabela: código equivalente do fato}. Ex.:
    # "Viagens" (2002) → "Viagens esporádicas" (2008 e 2018). Registrar nas notas.
    recode_categories: dict[str, dict[str, str]] = Field(default_factory=dict)
    # Séries compostas de fontes distintas (ADR-0022), aplicadas antes das regras acima:
    # - ``variable``: código da variável nesta tabela, se diferente do indicador;
    # - ``levels``: níveis SIDRA usados desta tabela ("6" = município); vazio: todos;
    # - ``scale``: multiplica o valor (mil unidades → unidades: 1000);
    # - ``complement``: troca o valor por complement - valor (analfabetismo → alfabetização);
    # - ``unit``: unidade publicada depois da transformação (a do indicador);
    # - ``aggregate``: soma categorias numa categoria-alvo, sem retirar as somadas;
    # - ``drop_categories``: dimensão → categorias desta tabela que saem do fato.
    variable: str | None = Field(default=None, pattern=r"^\d{1,8}$")
    levels: tuple[str, ...] = ()
    # Períodos desta tabela que ficam fora (o ano coberto por outra fonte da série).
    exclude_periods: tuple[str, ...] = ()
    scale: float = Field(default=1.0, gt=0)
    complement: float | None = None
    unit: str | None = None
    aggregate: tuple[AggregateRule, ...] = ()
    drop_categories: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    # Dimensão → categorias desta tabela que ficam (as demais linhas saem). Ex.: só a
    # idade "15 anos ou mais" da PNAD, quando a série não detalha a idade.
    keep_categories: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    def transforms(self) -> bool:
        """A regra muda valores ou linhas (além de renomear e recodificar)?"""
        return bool(
            self.levels
            or self.exclude_periods
            or self.scale != 1.0
            or self.complement is not None
            or self.unit
            or self.aggregate
            or self.drop_categories
            or self.keep_categories
        )


class FactConfig(_Strict):
    """Fato temático da Gold."""

    id: str = Field(pattern=TABLE_ID)
    dataset: str
    grain: str
    description: str
    # Classificação → coluna de chave de categoria no fato.
    classifications: dict[str, str] = Field(default_factory=dict)
    # Dimensões da Silver publicadas numa única categoria (em geral o Total),
    # sem classificação declarada: nome da dimensão → código da categoria. A
    # Gold confere que todas as observações têm essa categoria e retira a
    # dimensão (o fato fica sem desagregação). Usado pelos KPIs de Total do
    # panorama (ADR-0010), cujas classificações ainda não têm código conhecido.
    fixed_categories: dict[str, str] = Field(default_factory=dict)
    # Tabela de origem (código na Silver) → regras próprias, nas séries de tabelas.
    table_rules: dict[str, TableRule] = Field(default_factory=dict)

    def fixed_for(self, table_id: str) -> dict[str, str]:
        """Dimensões fixas das linhas de uma tabela de origem."""
        rule = self.table_rules.get(table_id)
        return {**self.fixed_categories, **(rule.fixed_categories if rule else {})}

    def has_fixed(self) -> bool:
        """O fato tem alguma dimensão fixa (geral ou de uma tabela)."""
        return bool(self.fixed_categories) or any(
            r.fixed_categories for r in self.table_rules.values()
        )


def _fixed_problems(fact: FactConfig, dimension_of: Mapping[str, str]) -> list[str]:
    """Dimensões fixas e regras por tabela de origem coerentes com o fato (ADR-0016)."""
    problems = []
    classified = {dimension_of[c] for c in fact.classifications if c in dimension_of}
    both = sorted(set(fact.fixed_categories) & classified)
    if both:
        problems.append(f"{fact.id}: dimensões fixas e classificadas ao mesmo tempo {both}")
    for table, rule in fact.table_rules.items():
        outside = sorted(set(rule.missing_as_total) - set(fact.classifications))
        if outside:
            problems.append(f"{fact.id}: missing_as_total da tabela {table} fora do fato {outside}")
        clash = sorted(set(rule.fixed_categories) & classified)
        if clash:
            problems.append(f"{fact.id}: dimensões fixas e classificadas na tabela {table} {clash}")
    return problems


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
    # Primeiro período publicado na Gold (código do SIDRA ou prefixo, como "1998"):
    # a Silver guarda a série inteira; a Gold mostra a partir daqui.
    first_period: str | None = Field(default=None, pattern=r"^\d{4,6}$")
    # Agregação no tempo (ADR-0013 e ADR-0017): como o trimestre, o semestre e o ano
    # saem dos períodos publicados.
    # - "sum": fluxos (ocorrências, óbitos, abates, PIB a preços correntes);
    # - "mean": números-índice (o índice anual da PMC, PMS e PIM é a média dos meses)
    #   e médias por período (rendimento médio, massa mensal, pessoas ocupadas);
    # - "last": acumulados em 12 meses e estimativas revisadas (o ano é o último mês).
    # Taxas sem regra oficial de agregação (desocupação, investimento) não declaram.
    # - "compound": variações percentuais encadeadas, (Π(1 + v/100) - 1) x 100 (o
    #   acumulado de um índice de preços a partir das variações mensais).
    time_aggregation: Literal["sum", "mean", "last", "compound"] | None = None


def _dimension_scope_problems(classifications: Sequence[Classification]) -> list[str]:
    """Cada dimensão da Silver tem no máximo uma classificação geral e, por dataset, uma."""
    problems = []
    general: dict[str, list[str]] = {}
    scoped: dict[tuple[str, str], list[str]] = {}
    for c in classifications:
        if not c.datasets:
            general.setdefault(c.silver_dimension, []).append(c.id)
        for ds in c.datasets:
            scoped.setdefault((c.silver_dimension, ds), []).append(c.id)
    for dim, ids in general.items():
        if len(ids) > 1:
            problems.append(f"dimensão {dim!r} em mais de uma classificação geral: {ids}")
    for (dim, ds), ids in scoped.items():
        if len(ids) > 1:
            problems.append(f"dimensão {dim!r} em mais de uma classificação para {ds}: {ids}")
    return problems


class PendingInstallation(_Strict):
    """Municípios com instalação prevista, segundo nota oficial."""

    dataset: str
    period: str
    # Pares (nome, sigla da UF), resolvidos para códigos na construção.
    municipalities: tuple[tuple[str, str], ...] = Field(min_length=1)
    source: str


class Consistency(_Strict):
    """Par de indicadores de tabelas diferentes que publicam os mesmos números.

    Os valores são comparados nas classificações comuns aos dois fatos, com as
    demais classificações de cada lado no Total. Serve para usar uma única
    tabela por KPI sem perder a conferência com as tabelas sobrepostas.
    """

    indicator: str = Field(pattern=INDICATOR_ID)
    reference: str = Field(pattern=INDICATOR_ID)
    note: str = ""


class GeometryLevel(_Strict):
    """Geometria de um nível territorial para mapas.

    Cada nível vem de uma malha oficial (``dataset``) ou é derivado pela união
    das geometrias de um nível com malha oficial (``derive_from``), agrupadas
    pelo ancestral na hierarquia territorial (``bridge_geography_ancestor``).
    """

    level: str = Field(pattern=INDICATOR_ID)
    dataset: str | None = None
    derive_from: str | None = Field(default=None, pattern=INDICATOR_ID)
    # Tolerância da simplificação (graus) e casas decimais das coordenadas.
    tolerance: float = Field(gt=0, le=1)
    decimals: int = Field(default=4, ge=2, le=6)

    @model_validator(mode="after")
    def _origin(self) -> GeometryLevel:
        if (self.dataset is None) == (self.derive_from is None):
            msg = f"geometria {self.level}: informe dataset ou derive_from (só um)"
            raise ValueError(msg)
        return self


class SemanticCatalog(_Strict):
    """Catálogo de um escopo de publicação."""

    config_version: str
    scope: str = Field(pattern=INDICATOR_ID)
    classifications: tuple[Classification, ...] = ()
    facts: tuple[FactConfig, ...] = Field(min_length=1)
    indicators: tuple[IndicatorConfig, ...] = Field(min_length=1)
    pending_installation: tuple[PendingInstallation, ...] = ()
    consistency: tuple[Consistency, ...] = ()
    geometry: tuple[GeometryLevel, ...] = ()
    # Hash do arquivo de origem, para a impressão digital da construção.
    content_sha256: str = ""

    @model_validator(mode="after")
    def _references(self) -> SemanticCatalog:  # noqa: PLR0912 - verificações independentes
        problems: list[str] = _dimension_scope_problems(self.classifications)
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
        dimension_of = {c.id: c.silver_dimension for c in self.classifications}
        for fact in self.facts:
            unknown = sorted(set(fact.classifications) - classes)
            if unknown:
                problems.append(f"{fact.id}: classificações não declaradas {unknown}")
            problems += _fixed_problems(fact, dimension_of)
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
        by_id = {i.id: i for i in self.indicators}
        for pair in self.consistency:
            left, right = by_id.get(pair.indicator), by_id.get(pair.reference)
            if left is None or right is None or left.id == right.id:
                problems.append(f"consistência inválida: {pair.indicator} x {pair.reference}")
            elif (left.concept, left.unit) != (right.concept, right.unit):
                problems.append(
                    f"consistência {left.id} x {right.id}: conceito ou unidade diferentes"
                )
            elif left.dataset == right.dataset:
                problems.append(f"consistência {left.id} x {right.id}: mesmo dataset")
        official = {g.level for g in self.geometry if g.dataset}
        levels = [g.level for g in self.geometry]
        for g in self.geometry:
            if levels.count(g.level) > 1:
                problems.append(f"geometria repetida para o nível {g.level}")
            if g.level not in LEVELS_BY_ID:
                problems.append(f"geometria: nível desconhecido {g.level}")
            elif g.derive_from is not None and (
                g.derive_from not in official or not is_ancestor_level(g.level, g.derive_from)
            ):
                problems.append(
                    f"geometria {g.level}: derive_from {g.derive_from} precisa ser um nível "
                    "com malha oficial e descendente dele"
                )
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

    def source_variable(self, indicator: IndicatorConfig, table: str) -> str:
        """Código da variável do indicador numa tabela da série (ADR-0022: pode mudar)."""
        rule = self.fact(indicator.fact).table_rules.get(table)
        return rule.variable if rule and rule.variable else indicator.variable

    def indicators_of(self, fact_id: str) -> list[IndicatorConfig]:
        """Indicadores (medidas) de um fato, na ordem do arquivo."""
        return [i for i in self.indicators if i.fact == fact_id]

    def geometry_datasets(self) -> list[str]:
        """Datasets de malha usados pela geometria, na ordem do arquivo."""
        return [g.dataset for g in self.geometry if g.dataset is not None]

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


# Listas que um fragmento (``<dir>/<escopo>/*.toml``) pode acrescentar ao catálogo.
_FRAGMENT_LISTS = (
    "classifications",
    "facts",
    "indicators",
    "pending_installation",
    "consistency",
)


def load_catalog(path: Path, fragments: Sequence[Path] = ()) -> SemanticCatalog:
    """Lê e valida um catálogo semântico, com os fragmentos acrescentados.

    Cada fragmento declara o mesmo ``scope`` e só acrescenta itens às listas
    de ``_FRAGMENT_LISTS``. O hash cobre o arquivo principal e os fragmentos.
    """
    digest = hashlib.sha256()
    extensions: list[dict[str, object]] = []
    try:
        content = path.read_bytes()
        digest.update(content)
        data = tomllib.loads(content.decode("utf-8"))
        for fragment in fragments:
            raw = fragment.read_bytes()
            digest.update(fragment.name.encode() + b"\0" + raw)
            extra = tomllib.loads(raw.decode("utf-8"))
            if extra.get("scope") != data.get("scope"):
                msg = f"{fragment}: escopo {extra.get('scope')!r} difere de {data.get('scope')!r}"
                raise SemanticConfigError(msg)
            allowed = {"config_version", "scope", "classification_partitions", *_FRAGMENT_LISTS}
            unknown = sorted(set(extra) - allowed)
            if unknown:
                msg = f"{fragment}: chaves não aceitas num fragmento: {unknown}"
                raise SemanticConfigError(msg)
            for key in _FRAGMENT_LISTS:
                data[key] = [*data.get(key, []), *extra.get(key, [])]
            extensions += extra.get("classification_partitions", [])
        # Partições acrescentadas por fragmentos a classificações declaradas em
        # outro arquivo (por exemplo, categorias de sexo da PNS na c2 curada).
        by_id = {c["id"]: c for c in data.get("classifications", [])}
        for ext in extensions:
            target = by_id.get(ext.get("classification"))
            if target is None:
                msg = f"partição para classificação não declarada: {ext.get('classification')}"
                raise SemanticConfigError(msg)
            part = {k: v for k, v in ext.items() if k != "classification"}
            target["partitions"] = [*target.get("partitions", []), part]
        return SemanticCatalog.model_validate({**data, "content_sha256": digest.hexdigest()})
    except (tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"{path}: catálogo semântico inválido: {exc}"
        raise SemanticConfigError(msg) from exc


def load_scope(config_dir: str | Path, scope: str) -> SemanticCatalog:
    """Catálogo do escopo (``<dir>/<escopo>.toml`` e os fragmentos ``<dir>/<escopo>/*.toml``)."""
    path = Path(config_dir) / f"{scope}.toml"
    if not path.is_file():
        msg = f"catálogo semântico do escopo {scope!r} não encontrado em {path}"
        raise SemanticConfigError(msg)
    fragments = sorted((Path(config_dir) / scope).glob("*.toml"))
    catalog = load_catalog(path, fragments)
    if catalog.scope != scope:
        msg = f"{path}: escopo declarado {catalog.scope!r} difere do nome do arquivo"
        raise SemanticConfigError(msg)
    return catalog
