"""Transformações Silver → Gold (Polars).

Funções puras, testáveis isoladamente. A orquestração, a qualidade e a escrita
ficam em ``odb_modeling.builder``.

Volume: o escopo demografia tem cerca de 500 mil observações. A leitura é
eager por isso (``collect`` único da Silver numa versão fixada), e as
transformações usam expressões nativas.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import polars as pl

from odb_modeling.contracts import (
    BRIDGE_PERIOD_ANCESTOR,
    DIM_BREAKDOWN,
    DIM_CATEGORY,
    DIM_CLASSIFICATION,
    DIM_INDICATOR,
    DIM_INDICATOR_NODE,
    DIM_PERIOD,
    INDICATOR_OBSERVATION,
)
from odb_processing.contracts import Contract
from odb_semantics import LEVELS, FactConfig, IndicatorConfig, SemanticCatalog
from odb_semantics.config import TableRule
from odb_semantics.periods import (
    TIME_AGGREGATION_NOTES,
    ancestor,
    coarser_grains,
    parse_period,
    parts,
)

# Níveis territoriais do SIDRA (coluna NC) → níveis internos. Conferidos pelos
# rótulos NN das respostas: 1 Brasil, 2 Grande Região, 3 Unidade da Federação,
# 6 Município; recortes especiais da tabela 9723 (2026-11-04): 131 Amazônia
# Legal, 134 Amazônia Legal de UF, 145 Território Quilombola por UF, 1145
# Território Quilombola; da 9954: 125 Terra Indígena por UF, 1124 Coordenação
# Regional da Funai, 1125 Terra Indígena (docs/data_catalog/ibge-niveis-territoriais.md).
SIDRA_LEVELS = {
    "1": "brasil",
    "2": "regiao",
    "3": "uf",
    "6": "municipio",
    "131": "amazonia_legal",
    "134": "amazonia_legal_uf",
    "145": "territorio_quilombola_uf",
    "1145": "territorio_quilombola",
    "125": "terra_indigena_uf",
    "1124": "coordenacao_regional_funai",
    "1125": "terra_indigena",
    "7": "regiao_metropolitana",
    "103": "areas_pof",
}
# Colunas da Silver ``sidra_observation`` que a Gold usa. As demais (linhagem da
# execução, URL de origem, nomes do nível e do período) ficam fora do build: a
# rastreabilidade da Gold vai pelo artefato Bronze e pela versão da Silver (KI-007).
SILVER_COLUMNS = (
    "table_id",
    "variable_id",
    "variable_name",
    "unit_name",
    "territorial_level",
    "territory_id",
    "territory_name",
    "period",
    "classification_key",
    "classifications",
    "value_raw",
    "value",
    "value_status",
    "value_decimals",
    "bronze_artifact_id",
    "bronze_checksum_sha256",
)
# Recorte municipal usado pelas siglas de UF e pelas notas de instalação prevista.
MUNICIPAL_NAME_COLUMNS = (
    "table_id",
    "period",
    "territorial_level",
    "territory_id",
    "territory_name",
)
NO_BREAKDOWN = "none"
ABSENT = "absent"
_RANK = {lv.id: lv.rank for lv in LEVELS}
_UF_SUFFIX = re.compile(r" - ([A-Z]{2})$")


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    """Dados de um dataset necessários à Gold."""

    dataset_id: str
    table_id: str
    reference_url: str | None
    license_id: str
    period_type: str = "ano"
    # Série de datasets (ex.: Sinesp VDE, um dataset por ano): as tabelas Silver de cada
    # membro. Vazio para um dataset único (a tabela é ``table_id``).
    table_ids: tuple[str, ...] = ()
    # Silver no desenho "Total e cada dimensão, as demais no Total" (Sinesp VDE, SIM): o
    # scan da Gold só lê as linhas que os fatos usam (``GoldBuilder._silver_scan``).
    marginals: bool = False

    @property
    def source_tables(self) -> tuple[str, ...]:
        """Tabelas Silver do dataset (uma, ou uma por membro da série)."""
        return self.table_ids or (self.table_id,)


def slug(text: str) -> str:
    """Identificador estável a partir de um rótulo (sem acentos, minúsculo)."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _conform(frame: pl.DataFrame, contract: Contract) -> pl.DataFrame:
    return frame.select(contract.frame_schema().names()).cast(contract.frame_schema())


# ------------------------------------------------------------------ observações


def indicator_map(catalog: SemanticCatalog, datasets: Mapping[str, DatasetInfo]) -> pl.DataFrame:
    """(tabela, variável) → indicador; uma linha por tabela da série, se houver."""
    return pl.DataFrame(
        [
            {
                "table_id": table,
                "variable_id": catalog.source_variable(i, table),
                "indicator_id": i.id,
                "dataset_id": i.dataset,
                "fact_table": i.fact,
                "fact_column": i.column,
            }
            for i in catalog.indicators
            for table in datasets[i.dataset].source_tables
        ]
    )


def dimension_map(catalog: SemanticCatalog, dataset: str | None = None) -> dict[str, str]:
    """Nome da dimensão na Silver → identificador da classificação.

    Sem ``dataset``, só as classificações gerais. Com ele, as classificações próprias do
    dataset (``datasets``) têm precedência: o "Sexo" do SIM é ``sexosim``, não a c2.
    """
    out = {c.silver_dimension: c.id for c in catalog.classifications if not c.datasets}
    if dataset is not None:
        out |= {c.silver_dimension: c.id for c in catalog.classifications if dataset in c.datasets}
    return out


def with_dataset(frame: pl.DataFrame) -> pl.DataFrame:
    """A coluna ``dataset_id`` (nula se faltar): sem ela, vale o mapa geral de dimensões."""
    if "dataset_id" in frame.columns:
        return frame
    return frame.with_columns(pl.lit(None, dtype=pl.String).alias("dataset_id"))


def by_dataset(catalog: SemanticCatalog, build: Callable[[dict[str, str]], pl.Expr]) -> pl.Expr:
    """Expressão com o mapa de dimensões de cada dataset (coluna ``dataset_id``).

    ``build`` recebe o mapa e devolve a expressão; os datasets com classificações
    próprias ganham um ramo, os demais usam o mapa geral.
    """
    expr = build(dimension_map(catalog))
    scoped = sorted({ds for c in catalog.classifications for ds in c.datasets})
    # Sem classificações próprias, a coluna ``dataset_id`` nem é consultada.
    for ds in scoped:
        expr = (
            pl.when(pl.col("dataset_id") == ds)
            .then(build(dimension_map(catalog, ds)))
            .otherwise(expr)
        )
    return expr


def select_silver(
    silver: pl.DataFrame, mapping: pl.DataFrame, catalog: SemanticCatalog | None = None
) -> pl.DataFrame:
    """Observações Silver das variáveis do catálogo, com o indicador correspondente.

    Com o catálogo, aplica ``first_period`` dos indicadores. A comparação é pelo
    código do SIDRA: "199712" < "1998" <= "199801", então um ano serve de corte
    para séries anuais, mensais e trimestrais.
    """
    selected = silver.join(mapping, on=["table_id", "variable_id"], how="inner")
    cuts = {i.id: i.first_period for i in (catalog.indicators if catalog else ()) if i.first_period}
    for indicator, first in cuts.items():
        selected = selected.filter(
            (pl.col("indicator_id") != indicator) | (pl.col("period") >= first)
        )
    return selected


def _renamed(rename: Mapping[str, str], recode: Mapping[str, Mapping[str, str]]) -> pl.Expr:
    """Struct da classificação com a dimensão renomeada e o código recodificado."""
    element = pl.element()
    dimension = element.struct.field("dimension")
    if rename:
        dimension = dimension.replace(dict(rename))
    category = element.struct.field("category_id")
    for dim, mapping in recode.items():
        category = (
            pl.when(dimension == dim).then(category.replace(dict(mapping))).otherwise(category)
        )
    return pl.struct(
        dimension.alias("dimension"),
        category.alias("category_id"),
        element.struct.field("category_name").alias("category_name"),
    )


def _with_key(frame: pl.DataFrame) -> pl.DataFrame:
    """Recalcula ``classification_key`` ("dimensão=categoria;...") das classificações."""
    pair = (
        pl.element().struct.field("dimension")
        + pl.lit("=")
        + pl.element().struct.field("category_id")
    )
    return frame.with_columns(
        pl.col("classifications").list.eval(pair).list.join(";").alias("classification_key")
    )


def _category_in(dimension: str) -> pl.Expr:
    """Categoria da linha numa dimensão (nula se a dimensão não aparecer)."""
    return (
        pl.col("classifications")
        .list.eval(
            pl.element()
            .filter(pl.element().struct.field("dimension") == dimension)
            .struct.field("category_id")
        )
        .list.first()
    )


def _aggregated(part: pl.DataFrame, rule: TableRule) -> pl.DataFrame:
    """Linhas novas: cada categoria-alvo como soma das categorias de origem (ADR-0022)."""
    out = []
    for agg in rule.aggregate:
        src = part.filter(_category_in(agg.dimension).is_in(list(agg.sources)))
        if src.is_empty():
            continue
        target = pl.struct(
            pl.lit(agg.dimension).alias("dimension"),
            pl.lit(agg.target).alias("category_id"),
            pl.lit(agg.name).alias("category_name"),
        )
        swapped = src.with_columns(
            pl.col("classifications").list.eval(
                pl.when(pl.element().struct.field("dimension") == agg.dimension)
                .then(target)
                .otherwise(pl.element())
            )
        )
        swapped = _with_key(swapped)
        quantitative = pl.col("value_status").is_in(["valid", "rounded_zero", "true_zero"])
        keys = [
            c
            for c in swapped.columns
            if c
            not in {
                "classifications",
                "value_raw",
                "value",
                "value_status",
                "value_decimals",
                "bronze_artifact_id",
                "bronze_checksum_sha256",
            }
        ]
        summed = swapped.group_by(keys, maintain_order=True).agg(
            pl.col("classifications").first(),
            pl.col("value").sum(),
            # Soma só com todas as partes publicadas; senão, sem valor.
            quantitative.all().alias("_complete"),
            pl.col("value_decimals").max(),
            pl.col("bronze_artifact_id").first(),
            pl.col("bronze_checksum_sha256").first(),
        )
        summed = summed.with_columns(
            pl.when(pl.col("_complete")).then(pl.col("value")).otherwise(None).alias("value"),
            pl.when(pl.col("_complete"))
            .then(pl.lit("valid"))
            .otherwise(pl.lit("not_available"))
            .alias("value_status"),
            # Valor bruto da soma (texto, como a fonte publica); "..." sem todas as partes.
            pl.when(pl.col("_complete"))
            .then(pl.col("value").cast(pl.String))
            .otherwise(pl.lit("..."))
            .alias("value_raw"),
        ).drop("_complete")
        out.append(summed.select(part.columns))
    return pl.concat(out, how="vertical_relaxed") if out else part.clear()


def apply_table_transforms(selected: pl.DataFrame, catalog: SemanticCatalog) -> pl.DataFrame:
    """Transformações das séries compostas de fontes distintas (ADR-0022).

    Por tabela da série (``table_rules``): níveis usados, escala, complemento, unidade,
    categorias somadas e retiradas. Roda antes de ``strip_fixed_categories``, que
    depois renomeia e recodifica.
    """
    if "table_id" not in selected.columns or "fact_table" not in selected.columns:
        return selected
    rules = [
        (fact, table, rule)
        for fact in catalog.facts
        for table, rule in fact.table_rules.items()
        if rule.transforms()
    ]
    if not rules:
        return selected
    handled = pl.lit(value=False)
    parts = []
    dtype = selected.schema["value"]
    for fact, table, rule in rules:
        here = (pl.col("fact_table") == fact.id) & (pl.col("table_id") == table)
        handled = handled | here
        part = selected.filter(here)
        if part.is_empty():
            continue
        if rule.levels:
            part = part.filter(pl.col("territorial_level").is_in(list(rule.levels)))
        if rule.exclude_periods:
            part = part.filter(~pl.col("period").is_in(list(rule.exclude_periods)))
        for dimension, codes in rule.keep_categories.items():
            part = part.filter(_category_in(dimension).is_in(list(codes)).fill_null(value=False))
        value = pl.col("value").cast(pl.Float64)
        if rule.scale != 1.0:
            value = value * rule.scale
        if rule.complement is not None:
            value = pl.lit(rule.complement) - value
        part = part.with_columns(value.round(6).cast(dtype).alias("value"))
        if rule.unit:
            part = part.with_columns(pl.lit(rule.unit).alias("unit_name"))
        extra = _aggregated(part, rule)
        for dimension, codes in rule.drop_categories.items():
            part = part.filter(~_category_in(dimension).is_in(list(codes)).fill_null(value=False))
        parts.extend([part, extra])
    return pl.concat([selected.filter(~handled), *parts], how="vertical_relaxed")


def strip_fixed_categories(
    selected: pl.DataFrame, catalog: SemanticCatalog
) -> tuple[pl.DataFrame, dict[str, dict[str, list[str]]]]:
    """Retira as dimensões de categoria fixa e completa o Total implícito (ADR-0016).

    Dimensões fixas: ``fixed_categories`` do fato e, nas séries de tabelas, as de
    ``table_rules`` de cada tabela de origem. A conferência é por tabela de origem:
    todas as linhas de cada tabela precisam estar na categoria declarada.

    Total implícito (``table_rules.missing_as_total``): a tabela não tem a
    classificação, e as linhas dela entram no Total (o valor é do universo inteiro).

    Devolve as observações ajustadas e as divergências encontradas:
    fato → dimensão → categorias observadas, quando alguma observação não
    está na categoria declarada (ou a dimensão não aparece).
    """
    facts = [f for f in catalog.facts if f.has_fixed() or f.table_rules]
    if not facts:
        return selected, {}
    if "table_id" not in selected.columns:  # quadros parciais (testes): uma tabela só
        out, found = strip_fixed_categories(
            selected.with_columns(pl.lit("").alias("table_id")), catalog
        )
        return out.drop("table_id"), found
    rows = selected.filter(pl.col("fact_table").is_in([f.id for f in facts]))
    observed = (
        rows.select("fact_table", "table_id", "classification_key", "classifications")
        .unique(["fact_table", "table_id", "classification_key"])
        .explode("classifications", empty_as_null=False)
        .with_columns(
            pl.col("classifications").struct.field("dimension").alias("dimension"),
            pl.col("classifications").struct.field("category_id").alias("category_id"),
        )
        .group_by("fact_table", "table_id", "dimension")
        .agg(pl.col("category_id").unique().sort())
    )
    seen = {
        (r["fact_table"], r["table_id"], r["dimension"]): [
            str(c) for c in r["category_id"] if c is not None
        ]
        for r in observed.iter_rows(named=True)
    }
    present = rows.select("fact_table", "table_id").unique()
    problems: dict[str, dict[str, list[str]]] = {}
    adjusted = pl.col("classifications")
    for fact in facts:
        tables = present.filter(pl.col("fact_table") == fact.id)["table_id"].to_list()
        for table in sorted(tables):
            fixed = fact.fixed_for(table)
            for dim, category in fixed.items():
                cats = seen.get((fact.id, table, dim), [])
                if cats != [category]:
                    bucket = problems.setdefault(fact.id, {}).setdefault(dim, [])
                    bucket[:] = sorted({*bucket, *cats})
            rule = fact.table_rules.get(table)
            implicit = [
                {
                    "dimension": catalog.classification(cid).silver_dimension,
                    "category_id": catalog.classification(cid).total,
                    "category_name": "Total",
                }
                for cid in (rule.missing_as_total if rule else ())
            ]
            here = (pl.col("fact_table") == fact.id) & (pl.col("table_id") == table)
            value = pl.col("classifications")
            renamed = bool(rule and (rule.rename_dimensions or rule.recode_categories))
            if rule and renamed:
                value = value.list.eval(_renamed(rule.rename_dimensions, rule.recode_categories))
            if fixed:
                value = value.list.eval(
                    pl.element().filter(~pl.element().struct.field("dimension").is_in(list(fixed)))
                )
            if implicit:
                value = value.list.concat(
                    pl.lit(implicit, dtype=selected.schema["classifications"])
                )
            if fixed or implicit or renamed:
                adjusted = pl.when(here).then(value).otherwise(adjusted)
    return selected.with_columns(adjusted.alias("classifications")), problems


def municipal_names(silver: pl.LazyFrame) -> pl.DataFrame:
    """Nomes publicados dos municípios por tabela e período (``MUNICIPAL_NAME_COLUMNS``).

    Basta para ``uf_abbreviations`` e ``resolve_pending_installation``, sem
    carregar as observações inteiras.
    """
    return (
        silver.filter(pl.col("territorial_level") == "6")
        .select(MUNICIPAL_NAME_COLUMNS)
        .unique()
        # Streaming: o scan passa por todas as Silvers, e o resultado é pequeno.
        .collect(engine="streaming")
    )


def uf_abbreviations(silver: pl.DataFrame) -> dict[str, str]:
    """Sigla de cada UF, extraída dos nomes municipais publicados ("Nome - UF")."""
    rows = (
        silver.filter(pl.col("territorial_level") == "6")
        .select(
            pl.col("territory_id").str.slice(0, 2).alias("uf_code"),
            pl.col("territory_name").str.extract(_UF_SUFFIX.pattern, 1).alias("abbr"),
        )
        .drop_nulls()
        .unique()
    )
    counts = rows.group_by("uf_code").agg(pl.col("abbr").n_unique().alias("n"), pl.col("abbr"))
    return {
        str(r["uf_code"]): str(r["abbr"][0]) for r in counts.iter_rows(named=True) if r["n"] == 1
    }


def resolve_pending_installation(
    catalog: SemanticCatalog, silver: pl.DataFrame, datasets: Mapping[str, DatasetInfo]
) -> tuple[dict[tuple[str, str], set[str]], list[dict[str, object]]]:
    """Resolve as notas de instalação prevista para códigos de município.

    Usa os nomes publicados no próprio dataset e período ("Nome - UF"). Devolve
    {(dataset, período): códigos} e o relatório de resolução (nomes não
    encontrados ou ambíguos ficam em ``problem``).
    """
    resolved: dict[tuple[str, str], set[str]] = {}
    report: list[dict[str, object]] = []
    for note in catalog.pending_installation:
        table = datasets[note.dataset].table_id
        rows = silver.filter(
            (pl.col("table_id") == table)
            & (pl.col("period") == note.period)
            & (pl.col("territorial_level") == "6")
        ).select("territory_id", "territory_name")
        rows = rows.unique()
        if rows.is_empty():
            report.append(
                {"dataset": note.dataset, "period": note.period, "problem": None, "applied": False}
            )
            continue
        codes: set[str] = set()
        for name, uf in note.municipalities:
            match = rows.filter(pl.col("territory_name") == f"{name} - {uf}")["territory_id"]
            if match.len() != 1:
                report.append(
                    {
                        "dataset": note.dataset,
                        "period": note.period,
                        "municipality": f"{name} - {uf}",
                        "problem": f"{match.len()} correspondências",
                        "applied": False,
                    }
                )
                continue
            codes.add(str(match[0]))
        resolved[(note.dataset, note.period)] = codes
        report.append(
            {
                "dataset": note.dataset,
                "period": note.period,
                "codes": sorted(codes),
                "problem": None,
                "applied": True,
            }
        )
    return resolved, report


def build_observations(
    selected: pl.DataFrame,
    catalog: SemanticCatalog,
    *,
    silver_version: int | Mapping[str, int],
    build_id: str,
    pending: Mapping[tuple[str, str], set[str]],
    period_types: Mapping[str, str] | None = None,
) -> pl.DataFrame:
    """Estrutura universal ``indicator_observation`` (§10.6).

    ``period_types`` (dataset → ``mes``/``trimestre``) converte o código SIDRA
    do período na chave da Gold (``gold_period``); sem tipo, o período é anual.
    """
    category_keys = by_dataset(
        catalog,
        lambda dims: (
            pl.col("classifications")
            .list.eval(
                pl.element().struct.field("dimension").replace_strict(dims, default=None)
                + pl.lit(":")
                + pl.element().struct.field("category_id")
            )
            .list.sort()
        ),
    )
    pending_keys = pl.DataFrame(
        [
            {"dataset_id": ds, "period": period, "geography_key": f"municipio:{code}"}
            for (ds, period), codes in pending.items()
            for code in codes
        ],
        schema={"dataset_id": pl.String, "period": pl.String, "geography_key": pl.String},
    ).with_columns(pl.lit(["pending_installation"]).alias("flags"))
    # Lazy: o plano junta as etapas e evita cópias intermediárias do quadro inteiro.
    frame = (
        selected.lazy()
        .with_columns(
            pl.col("territorial_level")
            .replace_strict(SIDRA_LEVELS, default=None)
            .alias("level_id"),
            category_keys.alias("category_keys"),
        )
        .with_columns(
            (pl.col("level_id") + pl.lit(":") + pl.col("territory_id")).alias("geography_key"),
            pl.when(pl.col("category_keys").list.len() == 0)
            .then(pl.lit(NO_BREAKDOWN))
            .otherwise(pl.col("category_keys").list.join("|"))
            .alias("breakdown_key"),
            pl.col("table_id").alias("source_table_id"),
            pl.col("variable_id").alias("source_variable_id"),
            pl.col("unit_name").alias("unit"),
            (
                pl.lit(silver_version, dtype=pl.Int64)
                if isinstance(silver_version, int)
                # Várias Silvers (IBGE, MJSP...): a versão da tabela de cada dataset.
                else pl.col("dataset_id").replace_strict(silver_version, return_dtype=pl.Int64)
            ).alias("silver_table_version"),
            pl.lit(build_id).alias("gold_build_id"),
        )
        .join(pending_keys.lazy(), on=["dataset_id", "period", "geography_key"], how="left")
        .with_columns(pl.col("flags").fill_null(pl.lit([], dtype=pl.List(pl.String))))
    )
    period = pl.col("period")
    for kind in ("mes", "trimestre"):
        ids = [d for d, t in (period_types or {}).items() if t == kind]
        if ids:
            period = (
                pl.when(pl.col("dataset_id").is_in(ids)).then(gold_period(kind)).otherwise(period)
            )
    frame = frame.with_columns(period.alias("period"))
    schema = INDICATOR_OBSERVATION.frame_schema()
    return (
        frame.select(schema.names())
        .cast(schema)
        .sort("indicator_id", "period", "geography_key", "breakdown_key")
        .collect()
    )


def gold_period(period_type: str) -> pl.Expr:
    """Código SIDRA do período → chave da Gold.

    Ano "2022" fica igual; mês "202609" vira "2026M09"; trimestre "202602"
    vira "2026T2". Assim períodos de tipos diferentes nunca colidem em
    ``dim_period`` e a ordem alfabética é a cronológica dentro de cada tipo.
    """
    code = pl.col("period")
    if period_type == "mes":
        return code.str.slice(0, 4) + pl.lit("M") + code.str.slice(4, 2)
    if period_type == "trimestre":
        return code.str.slice(0, 4) + pl.lit("T") + code.str.slice(5, 1)
    return code


def category_column(classification_id: str) -> pl.Expr:
    """Chave da categoria de uma classificação a partir de ``breakdown_key``."""
    return (
        pl.col("breakdown_key")
        .str.split("|")
        .list.eval(pl.element().filter(pl.element().str.starts_with(f"{classification_id}:")))
        .list.first()
    )


def build_fact(
    observations: pl.DataFrame, catalog: SemanticCatalog, fact: FactConfig, contract: Contract
) -> pl.DataFrame:
    """Fato temático (formato largo) a partir da estrutura universal."""
    indicators = catalog.indicators_of(fact.id)
    rows = observations.filter(pl.col("indicator_id").is_in([i.id for i in indicators]))
    rows = rows.with_columns(
        [category_column(cid).alias(col) for cid, col in fact.classifications.items()]
    )
    keys = ["geography_key", "level_id", "period", *fact.classifications.values()]
    base = rows.select(keys).unique()
    for ind in indicators:
        part = rows.filter(pl.col("indicator_id") == ind.id).select(
            *keys,
            pl.col("value").alias(ind.column),
            pl.col("value_status").alias(f"{ind.column}_status"),
        )
        base = base.join(part, on=keys, how="left", nulls_equal=True).with_columns(
            pl.col(f"{ind.column}_status").fill_null(ABSENT)
        )
    meta = rows.group_by(keys).agg(
        pl.col("silver_table_version").first(),
        pl.col("gold_build_id").first(),
        pl.col("flags").list.explode(keep_nulls=False, empty_as_null=False).unique().alias("flags"),
    )
    base = base.join(meta, on=keys, how="left", nulls_equal=True)
    if "pending_installation" in contract.schema:
        base = base.with_columns(
            pl.col("flags").list.contains("pending_installation").alias("pending_installation")
        )
    return _conform(base, contract).sort(*contract.key)


# ------------------------------------------------------------------ dimensões


def period_row(period: str) -> dict[str, object]:
    """Tipo, ano, intervalo de datas, posição na hierarquia e rótulos de um período."""
    p = parse_period(period)
    return {
        "period_type": p.grain,
        "year": p.year,
        "start": p.start,
        "end": p.end,
        "month": p.month,
        "quarter": p.quarter,
        "semester": p.semester,
        "label": p.label,
        "short_label": p.short_label,
    }


def build_dim_period(observations: pl.DataFrame) -> pl.DataFrame:
    """Períodos observados e os períodos maiores que os contêm (ADR-0013).

    Um mês observado traz também o trimestre, o semestre e o ano dele, para que a
    consulta agregada no tempo tenha rótulo e chave. Os períodos maiores só existem na
    dimensão: os valores deles são calculados na consulta, nunca gravados como oficiais.
    """
    periods = set(observations["period"].unique().to_list())
    for code in list(periods):
        for target in coarser_grains(parse_period(code).grain)[1:]:
            periods.add(ancestor(code, target))
    ordered = sorted(periods)
    rows = [period_row(p) for p in ordered]
    frame = pl.DataFrame(
        {
            "period": ordered,
            "period_type": [r["period_type"] for r in rows],
            "year": [r["year"] for r in rows],
            "start_date": [r["start"] for r in rows],
            "end_date": [r["end"] for r in rows],
            "month": [r["month"] for r in rows],
            "quarter": [r["quarter"] for r in rows],
            "semester": [r["semester"] for r in rows],
            "label": [r["label"] for r in rows],
            "short_label": [r["short_label"] for r in rows],
        },
        schema_overrides={"month": pl.Int16, "quarter": pl.Int16, "semester": pl.Int16},
    )
    return _conform(frame, DIM_PERIOD)


def build_bridge_period_ancestor(observations: pl.DataFrame) -> pl.DataFrame:
    """Cada período observado → períodos maiores que o contêm e quantas partes eles têm."""
    rows: list[dict[str, object]] = []
    for code in sorted(set(observations["period"].unique().to_list())):
        grain = parse_period(code).grain
        rows.extend(
            {
                "period": code,
                "ancestor_period": ancestor(code, target),
                "ancestor_type": target,
                "parts": parts(grain, target),
            }
            for target in coarser_grains(grain)[1:]
        )
    frame = pl.DataFrame(rows, schema=BRIDGE_PERIOD_ANCESTOR.frame_schema())
    return _conform(frame, BRIDGE_PERIOD_ANCESTOR)


def method_caveats(indicator: IndicatorConfig) -> list[str]:
    """Notas do indicador mais a nota de método da agregação no tempo (ADR-0017)."""
    out = list(indicator.caveats)
    note = TIME_AGGREGATION_NOTES.get(indicator.time_aggregation or "")
    if note and note not in out:
        out.append(note)
    return out


def time_grains(indicator: IndicatorConfig, periods: Sequence[str]) -> list[str]:
    """Grãos em que o indicador pode ser consultado (ADR-0013).

    Só indicadores com ``time_aggregation`` (soma, média ou último valor; ADR-0017)
    sobem na hierarquia; os demais ficam no grão publicado. Sem períodos, a lista
    fica vazia.
    """
    if not periods:
        return []
    grain = parse_period(periods[0]).grain
    return list(coarser_grains(grain)) if indicator.time_aggregation else [grain]


def category_names(selected: pl.DataFrame, catalog: SemanticCatalog) -> dict[str, str]:
    """Rótulo de cada categoria observada (o do período mais recente)."""
    keys = ["dataset_id", "period", "classification_key"]
    exploded = (
        with_dataset(selected)
        .select(*keys, "classifications")
        .unique(keys)
        .drop("classification_key")
        .explode("classifications", empty_as_null=False)
        .drop_nulls("classifications")
        .unnest("classifications")
    )
    if exploded.is_empty():
        return {}
    rows = (
        exploded.with_columns(
            (
                by_dataset(
                    catalog, lambda dims: pl.col("dimension").replace_strict(dims, default=None)
                )
                + pl.lit(":")
                + pl.col("category_id")
            ).alias("category_key")
        )
        .drop_nulls("category_key")
        .sort("period", descending=True)
        .unique("category_key", keep="first")
    )
    return dict(zip(rows["category_key"], rows["category_name"], strict=True))


def build_dim_classification(catalog: SemanticCatalog, used: Sequence[str]) -> pl.DataFrame:
    """Classificações usadas pelos fatos."""
    frame = pl.DataFrame(
        [
            {
                "classification_id": c.id,
                "name": c.name,
                "source_dimension": c.silver_dimension,
                "total_category_key": f"{c.id}:{c.total}",
                "partition_ids": [p.id for p in c.partitions],
            }
            for c in catalog.classifications
            if c.id in used
        ],
        schema=DIM_CLASSIFICATION.frame_schema(),
    )
    return _conform(frame, DIM_CLASSIFICATION)


def build_dim_category(
    catalog: SemanticCatalog, used: Sequence[str], names: Mapping[str, str]
) -> pl.DataFrame:
    """Categorias observadas, com a hierarquia curada (Total → partições, em vários níveis)."""
    rows: list[dict[str, object]] = []
    for c in catalog.classifications:
        if c.id not in used:
            continue
        for order, cat in enumerate(c.ordered()):
            key = f"{c.id}:{cat}"
            if cat == c.total:
                rows.append(
                    {
                        "category_key": key,
                        "classification_id": c.id,
                        "category_id": cat,
                        "name": names.get(key, "Total"),
                        "is_total": True,
                        "parent_category_key": None,
                        "partition_id": None,
                        "partition_label": None,
                        "partition_exhaustive": None,
                        "depth": 0,
                        "sort_order": 0,
                    }
                )
                continue
            if key not in names:
                continue
            part = c.partition_of(cat)
            assert part is not None  # noqa: S101 - toda categoria não Total tem partição
            rows.append(
                {
                    "category_key": key,
                    "classification_id": c.id,
                    "category_id": cat,
                    "name": names[key],
                    "is_total": False,
                    "parent_category_key": f"{c.id}:{c.parent_of(part)}",
                    "partition_id": part.id,
                    "partition_label": part.label,
                    "partition_exhaustive": part.exhaustive,
                    "depth": c.depth(cat),
                    "sort_order": order,
                }
            )
    return _conform(pl.DataFrame(rows, schema=DIM_CATEGORY.frame_schema()), DIM_CATEGORY)


def build_dim_breakdown(
    observations: pl.DataFrame, categories: pl.DataFrame, catalog: SemanticCatalog
) -> pl.DataFrame:
    """Combinações de categorias observadas, com rótulo legível."""
    info = {r["category_key"]: r for r in categories.iter_rows(named=True)}
    class_names = {c.id: c.name for c in catalog.classifications}
    rows: list[dict[str, object]] = []
    for key in sorted(observations["breakdown_key"].unique().to_list()):
        keys = [] if key == NO_BREAKDOWN else key.split("|")
        non_total = [k for k in keys if k in info and not info[k]["is_total"]]
        parts = [f"{class_names[k.split(':', 1)[0]]}: {info[k]['name']}" for k in non_total]
        if parts:
            label = "; ".join(parts)
        else:
            label = "Sem desagregação" if key == NO_BREAKDOWN else "Total"
        rows.append(
            {
                "breakdown_key": key,
                "label": label,
                "category_keys": keys,
                "classification_ids": [k.split(":", 1)[0] for k in keys],
                "non_total_classifications": sorted({k.split(":", 1)[0] for k in non_total}),
                "non_total_count": len(non_total),
            }
        )
    return _conform(pl.DataFrame(rows, schema=DIM_BREAKDOWN.frame_schema()), DIM_BREAKDOWN)


def indicator_stats(observations: pl.DataFrame) -> pl.DataFrame:
    """Níveis, períodos e número de observações de cada indicador."""
    return observations.group_by("indicator_id").agg(
        pl.col("level_id").unique().alias("levels"),
        pl.col("period").unique().sort().alias("periods"),
        pl.len().alias("n"),
    )


def build_dim_indicator(
    catalog: SemanticCatalog,
    stats: pl.DataFrame,
    variable_names: pl.DataFrame,
    datasets: Mapping[str, DatasetInfo],
    node_keys: Mapping[str, str],
) -> pl.DataFrame:
    """Catálogo de indicadores no release, com disponibilidade calculada dos dados.

    ``stats`` vem de ``indicator_stats``; ``variable_names`` traz ``indicator_id``,
    ``period`` e ``variable_name`` (vale o nome do período mais recente). Os dois podem
    ser resumos de vários lotes, com indicadores distintos em cada um.
    """
    by_indicator = {r["indicator_id"]: r for r in stats.iter_rows(named=True)}
    names = {
        r["indicator_id"]: r["variable_name"]
        for r in variable_names.sort("period", descending=True)
        .unique("indicator_id", keep="first")
        .iter_rows(named=True)
    }
    incompatible: dict[str, list[dict[str, str]]] = {i.id: [] for i in catalog.indicators}
    for pair, reason in catalog.incompatibilities().items():
        a, b = sorted(pair)
        incompatible[a].append({"indicator": b, "reason": reason})
        incompatible[b].append({"indicator": a, "reason": reason})
    rows = []
    for ind in catalog.indicators:
        st = by_indicator.get(ind.id, {"levels": [], "periods": [], "n": 0})
        ds = datasets[ind.dataset]
        rows.append(
            {
                "indicator_id": ind.id,
                "name": ind.name,
                "description": ind.description,
                "scope": catalog.scope,
                "dataset_id": ind.dataset,
                "source_table_id": ds.table_id,
                "source_variable_id": ind.variable,
                "source_variable_name": names.get(ind.id),
                "unit": ind.unit,
                "additivity": ind.additivity,
                "concept": ind.concept,
                "fact_table": ind.fact,
                "fact_column": ind.column,
                "theme_path": list(ind.path),
                "node_key": node_keys[ind.id],
                "classification_ids": list(catalog.fact(ind.fact).classifications),
                "available_levels": sorted(st["levels"], key=lambda lv: _RANK[lv]),
                "periods": list(st["periods"]),
                "observation_count": st["n"],
                "caveats": method_caveats(ind),
                "incompatible_with": sorted(incompatible[ind.id], key=lambda d: d["indicator"]),
                "reference_url": ds.reference_url,
                "license_id": ds.license_id,
                "time_aggregation": ind.time_aggregation,
                "time_grains": time_grains(ind, list(st["periods"])),
            }
        )
    return _conform(pl.DataFrame(rows, schema=DIM_INDICATOR.frame_schema()), DIM_INDICATOR)


def indicator_node_keys(catalog: SemanticCatalog) -> dict[str, str]:
    """Chave do nó de cada indicador na árvore temática."""
    return {i.id: "/".join([*(slug(p) for p in i.path), i.id]) for i in catalog.indicators}


def build_dim_indicator_node(
    catalog: SemanticCatalog, observations: pl.DataFrame, categories: pl.DataFrame
) -> pl.DataFrame:
    """Árvore temática: grupo → indicador → classificação → categoria."""
    cats = {r["category_key"]: r for r in categories.iter_rows(named=True)}
    classes = {c.id: c.name for c in catalog.classifications}
    used = (
        observations.select("indicator_id", "breakdown_key")
        .unique()
        .with_columns(pl.col("breakdown_key").str.split("|"))
        .explode("breakdown_key", empty_as_null=False)
        .unique()
    )
    used_by: dict[str, set[str]] = {}
    for r in used.iter_rows(named=True):
        used_by.setdefault(r["indicator_id"], set()).add(r["breakdown_key"])
    nodes: dict[str, dict[str, object]] = {}
    order = 0

    def add(key: str, parent: str | None, kind: str, labels: list[str], **extra: object) -> None:
        nonlocal order
        if key in nodes:
            return
        order += 1
        nodes[key] = {
            "node_key": key,
            "parent_key": parent,
            "node_type": kind,
            "label": labels[-1],
            "depth": len(labels) - 1,
            "path_labels": labels,
            "indicator_id": None,
            "classification_id": None,
            "category_key": None,
            "sort_order": order,
            **extra,
        }

    node_keys = indicator_node_keys(catalog)
    for ind in catalog.indicators:
        parent: str | None = None
        labels: list[str] = []
        for part in ind.path:
            labels = [*labels, part]
            key = "/".join(slug(p) for p in labels)
            add(key, parent, "group", labels)
            parent = key
        ind_key = node_keys[ind.id]
        ind_labels = [*labels, ind.name]
        add(ind_key, parent, "indicator", ind_labels, indicator_id=ind.id)
        for cid in catalog.fact(ind.fact).classifications:
            cls_key = f"{ind_key}/{cid}"
            cls_labels = [*ind_labels, classes[cid]]
            add(
                cls_key,
                ind_key,
                "classification",
                cls_labels,
                indicator_id=ind.id,
                classification_id=cid,
            )
            observed = sorted(
                (k for k in used_by.get(ind.id, set()) if k.startswith(f"{cid}:")),
                key=lambda k: cats[k]["sort_order"] if k in cats else 10**6,
            )
            category_nodes: dict[str, tuple[str, list[str]]] = {}
            for cat_key in observed:
                cat = cats.get(cat_key)
                if cat is None or cat["is_total"]:
                    continue
                parent_key, parent_labels = category_nodes.get(
                    str(cat["parent_category_key"]), (cls_key, cls_labels)
                )
                node_key = f"{cls_key}/{cat['category_id']}"
                labels = [*parent_labels, str(cat["name"])]
                add(
                    node_key,
                    parent_key,
                    "category",
                    labels,
                    indicator_id=ind.id,
                    classification_id=cid,
                    category_key=cat_key,
                )
                category_nodes[cat_key] = (node_key, labels)
    return _conform(
        pl.DataFrame(list(nodes.values()), schema=DIM_INDICATOR_NODE.frame_schema()),
        DIM_INDICATOR_NODE,
    )
