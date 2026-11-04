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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import polars as pl

from odb_modeling.contracts import (
    DIM_BREAKDOWN,
    DIM_CATEGORY,
    DIM_CLASSIFICATION,
    DIM_INDICATOR,
    DIM_INDICATOR_NODE,
    DIM_PERIOD,
    INDICATOR_OBSERVATION,
)
from odb_processing.contracts import Contract
from odb_semantics import LEVELS, FactConfig, SemanticCatalog

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
}
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


def slug(text: str) -> str:
    """Identificador estável a partir de um rótulo (sem acentos, minúsculo)."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _conform(frame: pl.DataFrame, contract: Contract) -> pl.DataFrame:
    return frame.select(contract.frame_schema().names()).cast(contract.frame_schema())


# ------------------------------------------------------------------ observações


def indicator_map(catalog: SemanticCatalog, datasets: Mapping[str, DatasetInfo]) -> pl.DataFrame:
    """(tabela, variável) → indicador."""
    return pl.DataFrame(
        [
            {
                "table_id": datasets[i.dataset].table_id,
                "variable_id": i.variable,
                "indicator_id": i.id,
                "dataset_id": i.dataset,
                "fact_table": i.fact,
                "fact_column": i.column,
            }
            for i in catalog.indicators
        ]
    )


def dimension_map(catalog: SemanticCatalog) -> dict[str, str]:
    """Nome da dimensão na Silver → identificador da classificação."""
    return {c.silver_dimension: c.id for c in catalog.classifications}


def select_silver(silver: pl.DataFrame, mapping: pl.DataFrame) -> pl.DataFrame:
    """Observações Silver das variáveis do catálogo, com o indicador correspondente."""
    return silver.join(mapping, on=["table_id", "variable_id"], how="inner")


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
    silver_version: int,
    build_id: str,
    pending: Mapping[tuple[str, str], set[str]],
) -> pl.DataFrame:
    """Estrutura universal ``indicator_observation`` (§10.6)."""
    dims = dimension_map(catalog)
    category_keys = (
        pl.col("classifications")
        .list.eval(
            pl.element().struct.field("dimension").replace_strict(dims, default=None)
            + pl.lit(":")
            + pl.element().struct.field("category_id")
        )
        .list.sort()
    )
    pending_keys = pl.DataFrame(
        [
            {"dataset_id": ds, "period": period, "geography_key": f"municipio:{code}"}
            for (ds, period), codes in pending.items()
            for code in codes
        ],
        schema={"dataset_id": pl.String, "period": pl.String, "geography_key": pl.String},
    ).with_columns(pl.lit(["pending_installation"]).alias("flags"))
    frame = (
        selected.with_columns(
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
            pl.lit(silver_version, dtype=pl.Int64).alias("silver_table_version"),
            pl.lit(build_id).alias("gold_build_id"),
        )
        .join(pending_keys, on=["dataset_id", "period", "geography_key"], how="left")
        .with_columns(pl.col("flags").fill_null(pl.lit([], dtype=pl.List(pl.String))))
    )
    return _conform(frame, INDICATOR_OBSERVATION).sort(
        "indicator_id", "period", "geography_key", "breakdown_key"
    )


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


def build_dim_period(observations: pl.DataFrame) -> pl.DataFrame:
    """Períodos observados. Nesta versão, só anos (outros tipos exigem decisão)."""
    periods = sorted(observations["period"].unique().to_list())
    not_annual = [p for p in periods if not re.fullmatch(r"\d{4}", p)]
    if not_annual:
        msg = f"períodos não anuais não suportados nesta versão do modelo: {not_annual[:10]}"
        raise ValueError(msg)
    frame = pl.DataFrame(
        {
            "period": periods,
            "period_type": ["ano"] * len(periods),
            "year": [int(p) for p in periods],
            "start_date": [date(int(p), 1, 1) for p in periods],
            "end_date": [date(int(p), 12, 31) for p in periods],
        }
    )
    return _conform(frame, DIM_PERIOD)


def category_names(selected: pl.DataFrame, catalog: SemanticCatalog) -> dict[str, str]:
    """Rótulo de cada categoria observada (o do período mais recente)."""
    dims = dimension_map(catalog)
    exploded = (
        selected.select("period", "classification_key", "classifications")
        .unique(["period", "classification_key"])
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
                pl.col("dimension").replace_strict(dims, default=None)
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


def build_dim_indicator(
    catalog: SemanticCatalog,
    observations: pl.DataFrame,
    selected: pl.DataFrame,
    datasets: Mapping[str, DatasetInfo],
    node_keys: Mapping[str, str],
) -> pl.DataFrame:
    """Catálogo de indicadores no release, com disponibilidade calculada dos dados."""
    stats = {
        r["indicator_id"]: r
        for r in observations.group_by("indicator_id")
        .agg(
            pl.col("level_id").unique().alias("levels"),
            pl.col("period").unique().sort().alias("periods"),
            pl.len().alias("n"),
        )
        .iter_rows(named=True)
    }
    names = {
        r["indicator_id"]: r["variable_name"]
        for r in selected.sort("period", descending=True)
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
        st = stats.get(ind.id, {"levels": [], "periods": [], "n": 0})
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
                "caveats": list(ind.caveats),
                "incompatible_with": sorted(incompatible[ind.id], key=lambda d: d["indicator"]),
                "reference_url": ds.reference_url,
                "license_id": ds.license_id,
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
