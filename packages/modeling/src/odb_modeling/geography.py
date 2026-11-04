"""Dimensão territorial e tabela de ancestrais (hierarquia macro → micro, §13).

A árvore vem da DTB vigente: Brasil → Grande Região → UF → Região
Intermediária → Região Imediata → Município. Territórios presentes nas
observações e ausentes da DTB (por exemplo, municípios extintos) entram com
``in_reference = false``. O pai deles é derivado da estrutura do código IBGE
(os dois primeiros dígitos do município são a UF; o primeiro dígito da UF é a
Grande Região), e não há vínculo com as regiões geográficas.

``bridge_geography_ancestor`` traz, para cada território, todos os seus
ancestrais, inclusive ele mesmo (distância 0). Com ela, "municípios da Bahia"
ou "soma até a UF" são junções simples.

Recortes especiais (territórios quilombolas, Amazônia Legal) vêm do SIDRA, não
da DTB. A parte do recorte numa UF (N145, N134) tem a UF como pai e o recorte
como ancestral adicional. Por isso a tabela de ancestrais é o fecho de um
grafo, não de uma árvore. Regras de código conferidas na API
(``docs/data_catalog/ibge-niveis-territoriais.md``): N145 = UF (2 dígitos) +
território (3 dígitos); N134 = UF.
"""

from __future__ import annotations

import polars as pl

from odb_modeling.contracts import BRIDGE_GEOGRAPHY_ANCESTOR, DIM_GEOGRAPHY
from odb_semantics import LEVELS, LEVELS_BY_ID


class GeographyError(ValueError):
    """Referência territorial inconsistente."""


SPECIAL_LEVELS = frozenset(lv.id for lv in LEVELS if lv.special)
# Níveis cujo código começa pelo código da UF (2 dígitos).
_UF_PREFIXED = ["municipio", "territorio_quilombola_uf", "amazonia_legal_uf"]
# Recortes nacionais (pai direto: Brasil).
_NATIONAL_SPECIAL = ["territorio_quilombola", "amazonia_legal"]


def _rows(level: str, frame: pl.DataFrame) -> pl.DataFrame:
    """Completa as colunas comuns de um nível."""
    lv = LEVELS_BY_ID[level]
    return frame.with_columns(
        pl.lit(level).alias("level_id"),
        pl.lit(lv.rank, dtype=pl.Int16).alias("level_rank"),
        pl.lit(lv.name).alias("level_name"),
        (pl.lit(f"{level}:") + pl.col("territory_code")).alias("geography_key"),
    )


def _single_parent(frame: pl.DataFrame, child: str, parent: str, what: str) -> None:
    counts = frame.group_by(child).agg(pl.col(parent).n_unique().alias("n")).filter(pl.col("n") > 1)
    if counts.height:
        msg = f"{what} com mais de um pai na DTB: {counts[child].head(10).to_list()}"
        raise GeographyError(msg)


def build_dim_geography(
    dtb: pl.DataFrame,
    observed: pl.DataFrame,
    *,
    reference: str,
    uf_abbreviations: dict[str, str],
) -> pl.DataFrame:
    """``dtb``: linhas de ``dtb_municipality`` de um ano; ``observed``: (level_id, code, name)."""
    _single_parent(dtb, "intermediate_region_id", "uf_id", "região intermediária")
    _single_parent(dtb, "immediate_region_id", "intermediate_region_id", "região imediata")
    null = pl.lit(None, dtype=pl.String)
    abbreviations = pl.DataFrame(
        {"uf_code": list(uf_abbreviations), "uf_abbreviation": list(uf_abbreviations.values())},
        schema={"uf_code": pl.String, "uf_abbreviation": pl.String},
    )
    parts = [
        _rows(
            "brasil",
            pl.DataFrame({"territory_code": ["1"], "name": ["Brasil"]}).with_columns(
                parent_key=null, region_code=null, uf_code=null
            ),
        ),
        _rows(
            "regiao",
            dtb.select(
                pl.col("region_id").alias("territory_code"),
                pl.col("region_name").alias("name"),
            )
            .unique()
            .with_columns(
                parent_key=pl.lit("brasil:1"),
                region_code=pl.col("territory_code"),
                uf_code=null,
            ),
        ),
        _rows(
            "uf",
            dtb.select(
                pl.col("uf_id").alias("territory_code"),
                pl.col("uf_name").alias("name"),
                pl.col("region_id").alias("region_code"),
            )
            .unique()
            .with_columns(
                parent_key=pl.lit("regiao:") + pl.col("region_code"),
                uf_code=pl.col("territory_code"),
            ),
        ),
        _rows(
            "regiao_intermediaria",
            dtb.select(
                pl.col("intermediate_region_id").alias("territory_code"),
                pl.col("intermediate_region_name").alias("name"),
                pl.col("region_id").alias("region_code"),
                pl.col("uf_id").alias("uf_code"),
            )
            .unique()
            .with_columns(parent_key=pl.lit("uf:") + pl.col("uf_code")),
        ),
        _rows(
            "regiao_imediata",
            dtb.select(
                pl.col("immediate_region_id").alias("territory_code"),
                pl.col("immediate_region_name").alias("name"),
                pl.col("region_id").alias("region_code"),
                pl.col("uf_id").alias("uf_code"),
                pl.col("intermediate_region_id").alias("intermediate_region_code"),
            )
            .unique()
            .with_columns(
                parent_key=pl.lit("regiao_intermediaria:") + pl.col("intermediate_region_code")
            ),
        ),
        _rows(
            "municipio",
            dtb.select(
                pl.col("municipality_id").alias("territory_code"),
                pl.col("municipality_name").alias("name"),
                pl.col("region_id").alias("region_code"),
                pl.col("uf_id").alias("uf_code"),
                pl.col("intermediate_region_id").alias("intermediate_region_code"),
                pl.col("immediate_region_id").alias("immediate_region_code"),
            ).with_columns(parent_key=pl.lit("regiao_imediata:") + pl.col("immediate_region_code")),
        ),
    ]
    reference_rows = pl.concat(parts, how="diagonal_relaxed").with_columns(
        pl.lit(value=True).alias("in_reference"), pl.lit(reference).alias("reference")
    )

    # Territórios observados que não estão na DTB.
    known = set(reference_rows["geography_key"].to_list())
    extra = (
        observed.with_columns((pl.col("level_id") + ":" + pl.col("code")).alias("geography_key"))
        .filter(~pl.col("geography_key").is_in(list(known)))
        .unique("geography_key", keep="first")
    )
    frames = [reference_rows]
    if extra.height:
        code = pl.col("territory_code")
        orphan = extra.select(
            pl.col("geography_key"),
            pl.col("level_id"),
            pl.col("code").alias("territory_code"),
            pl.col("name"),
        ).with_columns(
            pl.col("level_id")
            .replace_strict({lv.id: lv.rank for lv in LEVELS}, return_dtype=pl.Int16)
            .alias("level_rank"),
            pl.col("level_id")
            .replace_strict({lv.id: lv.name for lv in LEVELS}, return_dtype=pl.String)
            .alias("level_name"),
            pl.when(pl.col("level_id").is_in(_UF_PREFIXED))
            .then(pl.lit("uf:") + code.str.slice(0, 2))
            .when(pl.col("level_id") == "uf")
            .then(pl.lit("regiao:") + code.str.slice(0, 1))
            .when(pl.col("level_id").is_in(["regiao", *_NATIONAL_SPECIAL]))
            .then(pl.lit("brasil:1"))
            .otherwise(None)
            .alias("parent_key"),
            pl.when(pl.col("level_id").is_in(["uf", "regiao", *_UF_PREFIXED]))
            .then(code.str.slice(0, 1))
            .alias("region_code"),
            pl.when(pl.col("level_id").is_in(["uf", *_UF_PREFIXED]))
            .then(code.str.slice(0, 2))
            .alias("uf_code"),
            pl.lit(value=False).alias("in_reference"),
            pl.when(pl.col("level_id").is_in(list(SPECIAL_LEVELS)))
            .then(pl.lit("SIDRA: recorte territorial especial"))
            .otherwise(pl.lit("observações (ausente da referência)"))
            .alias("reference"),
        )
        frames.append(orphan)
    frame = (
        pl.concat(frames, how="diagonal_relaxed")
        .join(abbreviations, on="uf_code", how="left")
        .sort("level_rank", "territory_code")
    )
    for column in DIM_GEOGRAPHY.schema:
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None).alias(column))
    return frame.select(DIM_GEOGRAPHY.frame_schema().names()).cast(DIM_GEOGRAPHY.frame_schema())


def extra_ancestor_edges(geography: pl.DataFrame) -> pl.DataFrame:
    """Arestas além do pai: a parte do recorte numa UF também pertence ao recorte."""
    code = pl.col("territory_code")
    edges = geography.select(
        pl.col("geography_key").alias("child_key"),
        pl.when(pl.col("level_id") == "territorio_quilombola_uf")
        .then(
            pl.lit("territorio_quilombola:")
            + code.str.slice(2).cast(pl.Int64, strict=False).cast(pl.String)
        )
        .when(pl.col("level_id") == "amazonia_legal_uf")
        .then(pl.lit("amazonia_legal:131"))
        .otherwise(None)
        .alias("parent_key"),
    ).drop_nulls("parent_key")
    # Só liga a recortes presentes na dimensão.
    return edges.filter(pl.col("parent_key").is_in(geography["geography_key"].implode()))


def build_ancestor_bridge(geography: pl.DataFrame) -> pl.DataFrame:
    """Fecho transitivo das relações de pertencimento, inclusive o próprio território.

    Usa o pai de cada território e as arestas adicionais dos recortes
    especiais. Quando um ancestral é alcançado por dois caminhos, fica a menor
    distância.
    """
    nodes = geography.select("geography_key", "parent_key", "level_id", "level_rank")
    level_of = nodes.select(
        pl.col("geography_key").alias("ancestor_key"),
        pl.col("level_id").alias("ancestor_level"),
        pl.col("level_rank").alias("ancestor_rank"),
    )
    edges = pl.concat(
        [
            nodes.select(pl.col("geography_key").alias("child_key"), "parent_key").drop_nulls(
                "parent_key"
            ),
            extra_ancestor_edges(geography),
        ]
    ).unique()
    current = nodes.select(
        "geography_key",
        pl.col("geography_key").alias("ancestor_key"),
        pl.lit(0, dtype=pl.Int16).alias("distance"),
    )
    found = [current]
    for _ in range(2 * len(LEVELS) + 1):
        step = (
            current.join(edges, left_on="ancestor_key", right_on="child_key", how="inner")
            .select(
                "geography_key",
                pl.col("parent_key").alias("ancestor_key"),
                (pl.col("distance") + 1).cast(pl.Int16).alias("distance"),
            )
            .unique()
        )
        if step.is_empty():
            break
        found.append(step)
        current = step
    else:
        msg = "hierarquia territorial com ciclo ou profundidade inesperada"
        raise GeographyError(msg)
    bridge = (
        pl.concat(found)
        .group_by("geography_key", "ancestor_key")
        .agg(pl.col("distance").min())
        .join(level_of, on="ancestor_key", how="left")
    )
    if bridge["ancestor_level"].null_count():
        missing = bridge.filter(pl.col("ancestor_level").is_null())["ancestor_key"].unique()
        msg = f"pais inexistentes na dimensão territorial: {missing.head(10).to_list()}"
        raise GeographyError(msg)
    return (
        bridge.select(BRIDGE_GEOGRAPHY_ANCESTOR.frame_schema().names())
        .cast(BRIDGE_GEOGRAPHY_ANCESTOR.frame_schema())
        .sort("geography_key", "distance", "ancestor_key")
    )
