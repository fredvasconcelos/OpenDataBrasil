"""Gold das contas públicas: dimensões, fatos e agregados (ADR-0030 a 0034, ADR-0036).

Regras que não são óbvias:

* **As lentes nunca se somam** (ADR-0030). Cada fato e cada linha de agregado diz a lente
  (``A`` transferências, ``B`` pagamentos por favorecido); a lente C não tem território.
* **Território** (ADR-0032): o município vem da Silver. Sem município, a linha fica na
  UF; sem UF válida (exterior, sem informação, múltiplo), fica só no Brasil. A região é a
  soma das UFs, e o Brasil é a soma de tudo (inclusive o que não tem UF).
* **Ranking** (ADR-0031, decisão 2; ADR-0034, decisão 4): lançamentos agregados, fluxos
  dentro da União, intermediários financeiros, sigilosos e sem informação ficam fora dos
  rankings de destinatários, mas continuam nos totais.
* **Completude** (ADR-0036): a lente A é conferida com o pago (mais restos a pagar pagos)
  da lente C nas modalidades de transferência, por mês e ação.
* **FPM pelo Tesouro** (ADR-0038): o FPM da lente A é conferido, por município e mês, com
  a distribuição do Tesouro. Nos meses em que o total da lente A fica abaixo do Tesouro
  (acima da tolerância por ação), entra uma linha por município com a diferença, marcada
  ``value_source = "tesouro_fpm"``. Nos demais meses, nada muda.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import polars as pl

from odb_modeling.contas_contracts import (
    AGG_CONTAS_PERIOD_STATUS,
    AGG_CONTAS_TERRITORY,
    AGG_FPM_RECONCILIATION,
    AGG_RECIPIENT_RANK,
    AGG_TRANSFER_RECONCILIATION,
    DIM_AMENDMENT_AUTHOR,
    DIM_BUDGET_ACTION,
    DIM_EXPENSE_NATURE,
    DIM_MANAGEMENT_UNIT,
    DIM_RECIPIENT,
    FACT_FEDERAL_BUDGET_EXECUTION,
    FACT_FEDERAL_PAYMENT_RECIPIENT,
    FACT_FEDERAL_TRANSFER,
)
from odb_processing.contracts import Contract
from odb_processing.datasus import UF_CODES
from odb_processing.values import VALUE_DTYPE

LENS_TRANSFERS = "A"
LENS_PAYMENTS = "B"
LENS_EXECUTION = "C"

# Modalidades de aplicação que são transferência a outro ente ou entidade (MTO): 30/31
# estados e DF, 35/36 estados por fundo a fundo e consórcios, 40/41 municípios, 45/46
# municípios por fundo a fundo e consórcios, 50 entidades privadas sem fins lucrativos,
# 60 com fins lucrativos, 70/71 instituições multigovernamentais e consórcios, 80 exterior.
TRANSFER_MODALITIES = ("30", "31", "35", "36", "40", "41", "45", "46", "50", "60", "70", "71", "80")

# Classes fora do ranking de destinatários (ADR-0031, decisão 2).
NOT_RANKED = (
    "lancamento_agregado",
    "unidade_gestora_federal",
    "instituicao_financeira",
    "sigiloso",
    "sem_informacao",
)
NATURAL_PERSON = ("pessoa_fisica", "pessoa_fisica_sem_cpf")

CLASS_LABELS: Mapping[str, str] = {
    "municipio": "Municípios (prefeituras)",
    "estado_df": "Estados e Distrito Federal",
    "fundo_municipal": "Fundos públicos municipais",
    "fundo_estadual": "Fundos públicos estaduais e do DF",
    "fundo_federal": "Fundos públicos federais",
    "outro_ente_publico": "Outros órgãos e entidades públicas",
    "empresa": "Empresas",
    "entidade_sem_fins_lucrativos": "Entidades sem fins lucrativos",
    "instituicao_financeira": "Instituições financeiras",
    "pessoa_fisica_com_cnpj": "Pessoas físicas com CNPJ",
    "organizacao_internacional": "Organizações internacionais",
    "pessoa_fisica": "Pessoas físicas",
    "pessoa_fisica_sem_cpf": "Pessoas físicas sem CPF",
    "exterior": "Favorecidos no exterior",
    "unidade_gestora_federal": "Unidades gestoras federais",
    "lancamento_agregado": "Lançamentos agregados do Tesouro e da rede bancária",
    "sigiloso": "Sigiloso na fonte",
    "sem_informacao": "Sem informação na fonte",
    "nao_classificado": "Não classificado",
}

# Mês com falta acima desta fração do pago na lente C é "incompleto" (ADR-0036). Medido
# em 2024-01 a 2026-09: meses sem lacuna conhecida até 2,4%; meses com lacuna, 6,7% ou mais.
INCOMPLETE_SHARE = 0.05
# Ação conferida: diferença até 1% ou R$ 1 milhão, o que for maior.
ACTION_TOLERANCE_SHARE = 0.01
ACTION_TOLERANCE_VALUE = 1_000_000.0

# Origem do valor no fato da lente A (ADR-0038).
SOURCE_CGU = "cgu"
SOURCE_TREASURY_FPM = "tesouro_fpm"
FPM_ACTION = "0045"
# Diferença por município considerada igual (centavo; os dois arquivos vêm do SIAFI).
FPM_CENT = 0.005

LEVELS = ("municipio", "uf", "regiao", "brasil")
_UF = pl.DataFrame(
    {"uf": list(UF_CODES), "uf_code": list(UF_CODES.values())},
    schema={"uf": pl.String, "uf_code": pl.String},
)
UF_ABBREVIATIONS: Mapping[str, str] = {code: uf for uf, code in UF_CODES.items()}


# ------------------------------------------------------------------ tempo e território


def gold_period(column: str = "period") -> pl.Expr:
    """``202401`` (Silver) → ``2024M01`` (Gold, ADR-0013)."""
    col = pl.col(column)
    return col.str.slice(0, 4) + pl.lit("M") + col.str.slice(4, 2)


def with_territory(frame: pl.LazyFrame) -> pl.LazyFrame:
    """Código da UF e chave territorial mais específica de cada linha (ADR-0032).

    O município manda: a UF vem do código IBGE dele. Sem município, vale a sigla da UF da
    fonte, quando é uma das 27. Sem as duas, a linha fica só no Brasil.
    """
    municipality = pl.col("municipality_id")
    return (
        frame.join(_UF.lazy(), on="uf", how="left")
        .with_columns(
            pl.when(municipality.is_not_null())
            .then(municipality.str.slice(0, 2))
            .otherwise(pl.col("uf_code"))
            .alias("uf_code")
        )
        .with_columns(
            pl.when(municipality.is_not_null())
            .then(pl.lit("municipio:") + municipality)
            .when(pl.col("uf_code").is_not_null())
            .then(pl.lit("uf:") + pl.col("uf_code"))
            .otherwise(pl.lit("brasil:1"))
            .alias("geography_key")
        )
    )


# ------------------------------------------------------------------ dimensões


def _latest(columns: Sequence[str]) -> list[pl.Expr]:
    """O valor mais recente de cada coluna (o nome vigente no último mês em que aparece)."""
    return [pl.col(c).sort_by("period").last().alias(c) for c in columns]


def _keyed(
    frame: pl.DataFrame, natural: Sequence[str], key: str, dtype: pl.DataType
) -> pl.DataFrame:
    """Chave técnica pela ordem da chave natural: estável para a mesma entrada."""
    return (
        frame.sort(list(natural), nulls_last=True)
        .with_row_index(key, offset=1)
        .with_columns(pl.col(key).cast(dtype))
    )


def _conform(frame: pl.DataFrame, contract: Contract) -> pl.DataFrame:
    return frame.select(
        [
            (pl.col(n) if n in frame.columns else pl.lit(None)).cast(t).alias(n)
            for n, t in contract.schema.items()
        ]
    )


@dataclass(frozen=True, slots=True)
class RecipientDimension:
    """``dim_recipient`` e o número de favorecidos com classes diferentes entre lentes."""

    frame: pl.DataFrame
    class_conflicts: int


def build_dim_recipient(
    transfers: pl.LazyFrame, payments: pl.LazyFrame, legal_entities: pl.DataFrame
) -> RecipientDimension:
    """Favorecidos das lentes A e B pela chave código + nome (ADR-0031, decisão 3).

    ``legal_entities``: instantâneo mais recente do cadastro PJ (descrições de natureza e
    CNAE). A classe é a do mês mais recente; quando as lentes discordam (o tipo de
    favorecido estadual só existe na A), fica a da lente A, e a divergência é contada.
    """
    cols = ["recipient_code", "recipient_name", "recipient_class", "legal_nature_code", "period"]
    both = pl.concat(
        [
            transfers.select(cols).with_columns(pl.lit(LENS_TRANSFERS).alias("lens")),
            payments.select(cols).with_columns(pl.lit(LENS_PAYMENTS).alias("lens")),
        ]
    )
    # A lente A vence: a classe é ordenada pela lente (A depois de B) e depois pelo mês.
    ordered = pl.col("lens") == LENS_TRANSFERS
    grouped = (
        both.group_by("recipient_code", "recipient_name")
        .agg(
            pl.col("recipient_class").sort_by([ordered, "period"]).last(),
            pl.col("legal_nature_code").sort_by([ordered, "period"]).last(),
            (pl.col("lens") == LENS_TRANSFERS).any().alias("in_transfers"),
            (pl.col("lens") == LENS_PAYMENTS).any().alias("in_payments"),
            pl.col("recipient_class").n_unique().alias("_classes"),
        )
        .collect(engine="streaming")
    )
    conflicts = int((grouped["_classes"] > 1).sum())
    entities = legal_entities.select(
        "recipient_code",
        "legal_nature_description",
        "cnae_code",
        "cnae_description",
        "cnae_section_code",
        "cnae_section_description",
        pl.col("municipality_name_source").alias("seat_municipality_name"),
        pl.col("uf").alias("seat_uf"),
    ).unique("recipient_code", keep="first")
    frame = (
        grouped.drop("_classes")
        .join(entities, on="recipient_code", how="left")
        .with_columns(pl.col("recipient_class").is_in(NATURAL_PERSON).alias("is_natural_person"))
    )
    frame = _keyed(frame, ["recipient_code", "recipient_name"], "recipient_key", pl.Int64())
    frame = frame.with_columns(
        pl.Series(
            "recipient_id",
            [
                recipient_id(code, name)
                for code, name in zip(frame["recipient_code"], frame["recipient_name"], strict=True)
            ],
            dtype=pl.String,
        )
    )
    return RecipientDimension(_conform(frame, DIM_RECIPIENT), conflicts)


def recipient_id(code: str | None, name: str | None) -> str:
    """Identificador estável do favorecido: SHA-256 de código + nome, 16 hex (ADR-0036).

    Não revela nada além do que a fonte publica e é o mesmo em todos os releases.
    """
    raw = f"{code or ''}\x1f{name or ''}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def build_dim_management_unit(frames: Sequence[pl.LazyFrame]) -> pl.DataFrame:
    """Unidades gestoras pela chave órgão + UG, com o nome vigente e o órgão superior.

    A lente A não traz o órgão superior: ele vem das lentes B e C pelo código do órgão.
    """
    cols = ["organ_code", "management_unit_code", "management_unit_name", "organ_name"]
    sup = ["superior_organ_code", "superior_organ_name"]
    parts = [
        f.select(
            *cols,
            *[
                (pl.col(c) if c in f.collect_schema().names() else pl.lit(None, pl.String)).alias(c)
                for c in sup
            ],
            "period",
        )
        for f in frames
    ]
    rows = pl.concat(parts)
    units = (
        rows.group_by("organ_code", "management_unit_code")
        .agg(
            *_latest(["management_unit_name", "organ_name"]),
            pl.col("period").min().alias("first_period"),
            pl.col("period").max().alias("last_period"),
        )
        .collect(engine="streaming")
    )
    superior = (
        rows.filter(pl.col("superior_organ_code").is_not_null())
        .group_by("organ_code")
        .agg(*_latest(sup))
        .collect(engine="streaming")
    )
    frame = units.join(superior, on="organ_code", how="left", nulls_equal=True).with_columns(
        gold_period("first_period").alias("first_period"),
        gold_period("last_period").alias("last_period"),
    )
    frame = _keyed(frame, ["organ_code", "management_unit_code"], "ug_key", pl.Int32())
    return _conform(frame, DIM_MANAGEMENT_UNIT)


ACTION_KEY = ("fiscal_year", "function_code", "subfunction_code", "program_code", "action_code")


def build_dim_budget_action(frames: Sequence[pl.LazyFrame]) -> pl.DataFrame:
    """Funcional-programática por exercício: os códigos de programa mudam a cada PPA."""
    names = ["function_name", "subfunction_name", "program_name", "action_name"]
    parts = []
    for f in frames:
        has_language = "citizen_language" in f.collect_schema().names()
        parts.append(
            f.select(
                pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("fiscal_year"),
                *ACTION_KEY[1:],
                *names,
                (pl.col("citizen_language") if has_language else pl.lit(None, pl.String)).alias(
                    "citizen_language"
                ),
                "period",
            )
        )
    frame = (
        pl.concat(parts)
        .group_by(*ACTION_KEY)
        .agg(
            *_latest(names),
            pl.col("citizen_language").sort_by("period").drop_nulls().last(),
        )
        .collect(engine="streaming")
    )
    frame = _keyed(frame, ACTION_KEY, "action_key", pl.Int32())
    return _conform(frame, DIM_BUDGET_ACTION)


NATURE_KEY = ("expense_group_code", "application_modality_code", "expense_element_code")


def build_dim_expense_nature(
    frames: Sequence[pl.LazyFrame], execution: pl.LazyFrame
) -> pl.DataFrame:
    """Grupo, modalidade e elemento de despesa; a categoria econômica vem da lente C."""
    names = ["expense_group_name", "application_modality_name", "expense_element_name"]
    rows = pl.concat([f.select(*NATURE_KEY, *names, "period") for f in frames])
    frame = rows.group_by(*NATURE_KEY).agg(*_latest(names)).collect(engine="streaming")
    categories = (
        execution.select(
            "expense_group_code", "economic_category_code", "economic_category_name", "period"
        )
        .group_by("expense_group_code")
        .agg(*_latest(["economic_category_code", "economic_category_name"]))
        .collect(engine="streaming")
    )
    frame = frame.join(categories, on="expense_group_code", how="left", nulls_equal=True)
    frame = _keyed(frame, NATURE_KEY, "nature_key", pl.Int32())
    return _conform(frame, DIM_EXPENSE_NATURE)


def build_dim_amendment_author(execution: pl.LazyFrame) -> pl.DataFrame:
    """Autores de emenda da lente C (``-1``/"Sem informação" quando não há emenda)."""
    frame = (
        execution.select("amendment_author_code", "amendment_author_name", "period")
        .group_by("amendment_author_code")
        .agg(*_latest(["amendment_author_name"]))
        .collect(engine="streaming")
    )
    frame = _keyed(frame, ["amendment_author_code"], "author_key", pl.Int32())
    return _conform(frame, DIM_AMENDMENT_AUTHOR)


@dataclass(frozen=True, slots=True)
class Dimensions:
    """Dimensões com texto; os fatos recebem só as chaves."""

    recipient: pl.DataFrame
    management_unit: pl.DataFrame
    budget_action: pl.DataFrame
    expense_nature: pl.DataFrame
    amendment_author: pl.DataFrame

    def frames(self) -> dict[str, pl.DataFrame]:
        """Tabela → conteúdo."""
        return {
            DIM_RECIPIENT.name: self.recipient,
            DIM_MANAGEMENT_UNIT.name: self.management_unit,
            DIM_BUDGET_ACTION.name: self.budget_action,
            DIM_EXPENSE_NATURE.name: self.expense_nature,
            DIM_AMENDMENT_AUTHOR.name: self.amendment_author,
        }


def _join_keys(frame: pl.LazyFrame, dims: Dimensions, which: Sequence[str]) -> pl.LazyFrame:
    out = frame
    if "recipient" in which:
        out = out.join(
            dims.recipient.lazy().select("recipient_code", "recipient_name", "recipient_key"),
            on=["recipient_code", "recipient_name"],
            how="left",
            nulls_equal=True,
        )
    if "ug" in which:
        out = out.join(
            dims.management_unit.lazy().select("organ_code", "management_unit_code", "ug_key"),
            on=["organ_code", "management_unit_code"],
            how="left",
            nulls_equal=True,
        )
    if "action" in which:
        out = out.with_columns(
            pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("fiscal_year")
        ).join(
            dims.budget_action.lazy().select(*ACTION_KEY, "action_key"),
            on=list(ACTION_KEY),
            how="left",
            nulls_equal=True,
        )
    if "nature" in which:
        out = out.join(
            dims.expense_nature.lazy().select(*NATURE_KEY, "nature_key"),
            on=list(NATURE_KEY),
            how="left",
            nulls_equal=True,
        )
    if "author" in which:
        out = out.join(
            dims.amendment_author.lazy().select("amendment_author_code", "author_key"),
            on="amendment_author_code",
            how="left",
            nulls_equal=True,
        )
    return out


# ------------------------------------------------------------------ fatos


def _sum(column: str) -> pl.Expr:
    return pl.col(column).sum().cast(VALUE_DTYPE).alias(column)


_FACT_ORDER = ["uf_code", "municipality_id", "period", "recipient_key"]


def transfer_fact(silver: pl.LazyFrame, dims: Dimensions) -> pl.DataFrame:
    """Lente A no grão do fato (linhas da fonte somadas; a contagem fica em ``source_lines``)."""
    frame = _join_keys(with_territory(silver), dims, ("recipient", "ug", "action", "nature"))
    keys = [c for c in FACT_FEDERAL_TRANSFER.key if c != "period"]
    out = (
        frame.group_by("period", *keys, "uf_code", "municipality_id")
        .agg(
            _sum("value"),
            pl.len().cast(pl.Int32).alias("source_lines"),
            pl.col("recipient_class").first(),
        )
        .with_columns(gold_period(), pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"))
        .collect(engine="streaming")
    )
    # Ordem de território e favorecido: o DuckDB poda grupos de linhas pelos mín./máx.
    return _conform(out, FACT_FEDERAL_TRANSFER).sort(_FACT_ORDER, nulls_last=True)


def payment_fact(silver: pl.LazyFrame, dims: Dimensions) -> pl.DataFrame:
    """Lente B no grão do fato: mês x território da sede x favorecido x UG."""
    frame = _join_keys(with_territory(silver), dims, ("recipient", "ug"))
    keys = [c for c in FACT_FEDERAL_PAYMENT_RECIPIENT.key if c != "period"]
    out = (
        frame.group_by("period", *keys, "uf_code", "municipality_id")
        .agg(
            _sum("value"),
            pl.len().cast(pl.Int32).alias("source_lines"),
            pl.col("recipient_class").first(),
        )
        .with_columns(gold_period(), pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"))
        .collect(engine="streaming")
    )
    return _conform(out, FACT_FEDERAL_PAYMENT_RECIPIENT).sort(_FACT_ORDER, nulls_last=True)


EXECUTION_MEASURES = (
    "committed",
    "liquidated",
    "paid",
    "payables_registered",
    "payables_cancelled",
    "payables_paid",
)


def execution_fact(silver: pl.LazyFrame, dims: Dimensions) -> pl.DataFrame:
    """Lente C no grão do fato: mês x UG x ação x natureza x autor de emenda."""
    frame = _join_keys(silver, dims, ("ug", "action", "nature", "author"))
    keys = [c for c in FACT_FEDERAL_BUDGET_EXECUTION.key if c != "period"]
    out = (
        frame.group_by("period", *keys)
        .agg(*[_sum(m) for m in EXECUTION_MEASURES], pl.len().cast(pl.Int32).alias("source_lines"))
        .with_columns(gold_period(), pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"))
        .collect(engine="streaming")
    )
    return _conform(out, FACT_FEDERAL_BUDGET_EXECUTION)


# ------------------------------------------------------------------ agregados


def _levels(frame: pl.DataFrame) -> pl.DataFrame:
    """Repete cada linha nos níveis a que ela pertence: município, UF, região e Brasil."""
    municipality = pl.col("municipality_id")
    uf = pl.col("uf_code")
    parts = [
        frame.filter(municipality.is_not_null()).with_columns(
            pl.lit("municipio").alias("level_id"),
            (pl.lit("municipio:") + municipality).alias("geography_key"),
        ),
        frame.filter(uf.is_not_null()).with_columns(
            pl.lit("uf").alias("level_id"), (pl.lit("uf:") + uf).alias("geography_key")
        ),
        frame.filter(uf.is_not_null()).with_columns(
            pl.lit("regiao").alias("level_id"),
            (pl.lit("regiao:") + uf.str.slice(0, 1)).alias("geography_key"),
        ),
        frame.with_columns(
            pl.lit("brasil").alias("level_id"), pl.lit("brasil:1").alias("geography_key")
        ),
    ]
    return pl.concat(parts)


# Dimensão do "detalhar por" → (coluna do código, coluna do rótulo), por lente
# (ADR-0034, decisão 1). "total" é o mapa sem detalhamento.
TRANSFER_DIMENSIONS: Mapping[str, tuple[str, str]] = {
    "transfer_type": ("transfer_type", "transfer_type"),
    "function": ("function_code", "function_name"),
    "subfunction": ("subfunction_code", "subfunction_name"),
    "program": ("program_code", "program_name"),
    "action": ("action_code", "action_name"),
    "superior_organ": ("superior_organ_code", "superior_organ_name"),
    "organ": ("organ_code", "organ_name"),
    "expense_group": ("expense_group_code", "expense_group_name"),
    "application_modality": ("application_modality_code", "application_modality_name"),
    "expense_element": ("expense_element_code", "expense_element_name"),
    "recipient_class": ("recipient_class", "recipient_class_label"),
}
PAYMENT_DIMENSIONS: Mapping[str, tuple[str, str]] = {
    "superior_organ": ("superior_organ_code", "superior_organ_name"),
    "organ": ("organ_code", "organ_name"),
    "management_unit": ("management_unit_code", "management_unit_name"),
    "recipient_class": ("recipient_class", "recipient_class_label"),
    "cnae_section": ("cnae_section_code", "cnae_section_description"),
}
# Sem código na dimensão: categoria explícita, nunca nulo silencioso (§9.4).
MISSING_CODE = "-"
MISSING_LABEL = "Não se aplica ou sem informação"


def with_attributes(fact: pl.DataFrame, dims: Dimensions, lens: str) -> pl.DataFrame:
    """Fato com os atributos das dimensões que o "detalhar por" usa."""
    out = fact.join(
        dims.management_unit.select(
            "ug_key",
            "management_unit_code",
            "management_unit_name",
            "organ_code",
            "organ_name",
            "superior_organ_code",
            "superior_organ_name",
        ),
        on="ug_key",
        how="left",
    ).with_columns(
        pl.col("recipient_class")
        .replace_strict(dict(CLASS_LABELS), default=pl.col("recipient_class"))
        .alias("recipient_class_label")
    )
    if lens == LENS_TRANSFERS:
        out = out.join(
            dims.budget_action.drop("fiscal_year", "citizen_language"), on="action_key", how="left"
        ).join(dims.expense_nature, on="nature_key", how="left")
    else:
        out = out.join(
            dims.recipient.select("recipient_key", "cnae_section_code", "cnae_section_description"),
            on="recipient_key",
            how="left",
        )
    return out


def territory_aggregates(frame: pl.DataFrame, lens: str) -> pl.DataFrame:
    """``agg_contas_territory`` de um lote (um ano de uma lente).

    ``frame``: fato com atributos (``with_attributes``). Cada dimensão é somada por mês e
    território nos quatro níveis.
    """
    dimensions = TRANSFER_DIMENSIONS if lens == LENS_TRANSFERS else PAYMENT_DIMENSIONS
    base = ["year", "period", "municipality_id", "uf_code"]
    parts = [
        frame.group_by(base)
        .agg(_sum("value"), pl.col("source_lines").sum().cast(pl.Int64))
        .with_columns(
            pl.lit("total").alias("dimension_id"),
            pl.lit("total").alias("category_code"),
            pl.lit("Total").alias("category_label"),
        )
    ]
    for dimension_id, (code, label) in dimensions.items():
        parts.append(
            frame.group_by(*base, pl.col(code).fill_null(MISSING_CODE).alias("category_code"))
            .agg(
                _sum("value"),
                pl.col("source_lines").sum().cast(pl.Int64),
                pl.col(label).drop_nulls().max().fill_null(MISSING_LABEL).alias("category_label"),
            )
            .with_columns(pl.lit(dimension_id).alias("dimension_id"))
        )
    detail = pl.concat(parts, how="diagonal")
    out = (
        _levels(detail)
        .group_by("level_id", "geography_key", "year", "period", "dimension_id", "category_code")
        .agg(
            _sum("value"),
            pl.col("source_lines").sum().cast(pl.Int64),
            pl.col("category_label").max(),
        )
        .with_columns(pl.lit(lens).alias("lens"))
    )
    # Ordenado por território: a consulta de um território lê um só grupo de linhas.
    return _conform(out, AGG_CONTAS_TERRITORY).sort("geography_key", "dimension_id", "period")


def recipient_rank(fact: pl.DataFrame, lens: str, top_n: int) -> pl.DataFrame:
    """Os ``top_n`` maiores destinatários por território e ano (ADR-0034, decisão 4).

    O território inclui os favorecidos de todos os municípios dele e os sem município da
    UF. Empate: a chave do favorecido (ordem de código e nome) decide.
    """
    ranked = fact.filter(~pl.col("recipient_class").is_in(NOT_RANKED))
    columns = ["year", "municipality_id", "uf_code", "recipient_key", "recipient_class"]
    totals = (
        _levels(ranked.select(*columns, "value", "source_lines"))
        .group_by("level_id", "geography_key", "year", "recipient_key")
        .agg(
            _sum("value"),
            pl.col("source_lines").sum().cast(pl.Int64),
            pl.col("recipient_class").first(),
        )
    )
    window = ["geography_key", "year"]
    out = (
        totals.sort(["value", "recipient_key"], descending=[True, False])
        .with_columns(
            pl.col("recipient_key").cum_count().over(window).cast(pl.Int32).alias("rank"),
            pl.len().over(window).cast(pl.Int64).alias("recipients_in_territory"),
        )
        .filter(pl.col("rank") <= top_n)
        .with_columns(pl.lit(lens).alias("lens"))
    )
    return _conform(out, AGG_RECIPIENT_RANK).sort("geography_key", "year", "rank")


# ------------------------------------------------------------------ FPM pelo Tesouro


@dataclass(frozen=True, slots=True)
class FpmComplement:
    """Complemento do FPM (linhas no formato da Silver da lente A) e a conferência."""

    rows: pl.DataFrame
    reconciliation: pl.DataFrame
    negative: pl.DataFrame  # município x mês complementado com o Tesouro abaixo da CGU
    without_template: pl.DataFrame  # município sem linha de FPM na lente A para copiar


def _fpm_months(transfers: pl.LazyFrame, treasury: pl.LazyFrame) -> pl.DataFrame:
    """Meses da lente A com o FPM total abaixo do Tesouro além da tolerância por ação."""
    lens_a = transfers.select("period").unique()
    a = (
        transfers.filter(pl.col("action_code") == FPM_ACTION)
        .group_by("period")
        .agg(pl.col("value").sum().cast(pl.Float64).alias("a"))
    )
    t = treasury.group_by("period").agg(pl.col("value").sum().cast(pl.Float64).alias("t"))
    tolerance = pl.max_horizontal(pl.col("t") * ACTION_TOLERANCE_SHARE, ACTION_TOLERANCE_VALUE)
    return (
        lens_a.join(t, on="period")
        .join(a, on="period", how="left")
        .with_columns(pl.col("a").fill_null(0.0))
        .filter((pl.col("t") - pl.col("a")) > tolerance)
        .select("period")
        .collect()
    )


def fpm_complement(transfers: pl.LazyFrame, treasury: pl.LazyFrame) -> FpmComplement:
    """Conferência do FPM por município e mês e o complemento pelo Tesouro (ADR-0038).

    ``transfers``: Silver da lente A (períodos ``AAAAMM``); ``treasury``: Silver do FPM do
    Tesouro (``period``, ``municipality_id``, ``value``). Só entram os meses que existem na
    lente A. O complemento é ``Tesouro - lente A`` em cada município dos meses abaixo da
    tolerância; as demais colunas copiam a linha de FPM da prefeitura no mês mais recente
    até aquele (ou o primeiro depois), para manter favorecido, UG, ação e natureza.
    """
    months = _fpm_months(transfers, treasury)
    complemented = months["period"].to_list()
    fpm = transfers.filter(pl.col("action_code") == FPM_ACTION)
    lens_periods = transfers.select("period").unique()
    a_mun = (
        fpm.filter(pl.col("municipality_id").is_not_null())
        .group_by("period", "municipality_id")
        .agg(pl.col("value").sum().alias("value_transfers"))
    )
    t_mun = (
        treasury.filter(pl.col("municipality_id").is_not_null())
        .join(lens_periods, on="period")
        .group_by("period", "municipality_id")
        .agg(pl.col("value").sum().alias("value_treasury"))
    )
    zero = pl.lit(0).cast(VALUE_DTYPE)
    cent = (pl.col("value_treasury") - pl.col("value_transfers")).cast(pl.Float64).abs()
    joined = (
        t_mun.join(a_mun, on=["period", "municipality_id"], how="full", coalesce=True)
        .with_columns(
            pl.col("value_transfers").fill_null(zero).cast(VALUE_DTYPE),
            pl.col("value_treasury").fill_null(zero).cast(VALUE_DTYPE),
            pl.col("period").is_in(complemented).alias("_complemented"),
        )
        .with_columns(
            pl.when(pl.col("_complemented") & (cent > FPM_CENT))
            .then(pl.col("value_treasury") - pl.col("value_transfers"))
            .otherwise(zero)
            .cast(VALUE_DTYPE)
            .alias("complement"),
        )
        .with_columns(
            pl.when(pl.col("complement") != 0)
            .then(pl.lit("complementado"))
            .when(cent <= FPM_CENT)
            .then(pl.lit("conferido"))
            .otherwise(pl.lit("divergente"))
            .alias("status")
        )
        .collect()
    )
    reconciliation = _conform(
        joined.with_columns(
            pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"),
            (pl.lit("municipio:") + pl.col("municipality_id")).alias("geography_key"),
        ).with_columns(gold_period()),
        AGG_FPM_RECONCILIATION,
    ).sort("period", "municipality_id")
    wanted = joined.filter(pl.col("complement") != 0).select(
        "period", "municipality_id", pl.col("complement").alias("value")
    )
    negative = wanted.filter(pl.col("value") < 0)
    rows, without = _complement_rows(transfers, fpm, wanted)
    return FpmComplement(rows, reconciliation, negative, without)


def _complement_rows(
    transfers: pl.LazyFrame, fpm: pl.LazyFrame, wanted: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Linhas do complemento no schema da Silver da lente A, mais ``value_source``."""
    schema = transfers.collect_schema()
    columns = [c for c in schema.names() if c != "value_source"]
    if wanted.is_empty():
        empty = pl.DataFrame(schema={**schema, "value_source": pl.String})
        return empty.select([*columns, "value_source"]), wanted.select("municipality_id")
    templates = (
        fpm.filter(
            pl.col("municipality_id").is_in(wanted["municipality_id"].unique().to_list())
            & (pl.col("recipient_class") == "municipio")
        )
        .select(columns)
        .collect()
        .with_columns(pl.col("period").cast(pl.Int32).alias("_p"))
        .sort("value", descending=True)
        .unique(["municipality_id", "_p"], keep="first")
        .sort("_p")
    )
    target = wanted.with_columns(pl.col("period").cast(pl.Int32).alias("_p")).sort("_p")
    keep = ["municipality_id", "_p", "value", "period"]
    copied = templates.drop("value", "period")
    found = target.select(keep).join_asof(
        copied, on="_p", by="municipality_id", strategy="backward", check_sortedness=False
    )
    later = found.filter(pl.col("recipient_code").is_null()).select(keep)
    if later.height:
        later = later.join_asof(
            copied, on="_p", by="municipality_id", strategy="forward", check_sortedness=False
        )
        found = pl.concat([found.filter(pl.col("recipient_code").is_not_null()), later])
    without = found.filter(pl.col("recipient_code").is_null()).select("period", "municipality_id")
    rows = (
        found.filter(pl.col("recipient_code").is_not_null())
        .with_columns(
            pl.col("municipality_id")
            .str.slice(0, 2)
            .replace_strict(dict(UF_ABBREVIATIONS), default=None)
            .alias("uf"),
            pl.lit("municipio").alias("territory_status"),
            pl.col("value").cast(schema["value"]),
            pl.lit(SOURCE_TREASURY_FPM).alias("value_source"),
        )
        .select(*[pl.col(c).cast(schema[c]) for c in columns], "value_source")
        .sort("period", "municipality_id")
    )
    return rows, without


# ------------------------------------------------------------------ conferência e situação


def transfers_by_action(silver: pl.LazyFrame) -> pl.DataFrame:
    """Lente A por mês e ação, para a conferência com a lente C."""
    return (
        silver.group_by("period", "action_code")
        .agg(
            _sum("value").alias("value_transfers"),
            pl.col("action_name").max(),
            pl.col("transfer_type").mode().sort().first(),
        )
        .collect(engine="streaming")
    )


def execution_by_action(silver: pl.LazyFrame) -> pl.DataFrame:
    """Pago e restos a pagar pagos da lente C nas modalidades de transferência."""
    return (
        silver.filter(pl.col("application_modality_code").is_in(TRANSFER_MODALITIES))
        .group_by("period", "action_code")
        .agg(
            _sum("paid").alias("paid_execution"),
            _sum("payables_paid").alias("payables_paid_execution"),
            pl.col("action_name").max().alias("_execution_name"),
        )
        .collect(engine="streaming")
    )


def transfer_reconciliation(transfers: pl.DataFrame, execution: pl.DataFrame) -> pl.DataFrame:
    """A x C por mês e ação (ADR-0036, decisão 2). Só os meses presentes nas duas lentes."""
    zero = pl.lit(0).cast(VALUE_DTYPE)
    common = set(transfers["period"].unique()) & set(execution["period"].unique())
    frame = (
        transfers.filter(pl.col("period").is_in(list(common)))
        .join(
            execution.filter(pl.col("period").is_in(list(common))),
            on=["period", "action_code"],
            how="full",
            coalesce=True,
        )
        .with_columns(
            pl.col("action_name").fill_null(pl.col("_execution_name")),
            pl.col("value_transfers").fill_null(zero),
            pl.col("paid_execution").fill_null(zero),
            pl.col("payables_paid_execution").fill_null(zero),
        )
        .with_columns(
            (pl.col("paid_execution") + pl.col("payables_paid_execution")).alias("_execution")
        )
        .with_columns(
            pl.when(pl.col("_execution") > pl.col("value_transfers"))
            .then(pl.col("_execution") - pl.col("value_transfers"))
            .otherwise(zero)
            .cast(VALUE_DTYPE)
            .alias("shortfall"),
        )
    )
    a = pl.col("value_transfers").cast(pl.Float64)
    c = pl.col("_execution").cast(pl.Float64)
    tolerance = pl.max_horizontal(c.abs() * ACTION_TOLERANCE_SHARE, pl.lit(ACTION_TOLERANCE_VALUE))
    frame = frame.with_columns(
        pl.when((a - c).abs() <= tolerance)
        .then(pl.lit("conferido"))
        .when(a == 0)
        .then(pl.lit("ausente_nas_transferencias"))
        .when(c == 0)
        .then(pl.lit("ausente_na_execucao"))
        .when(a < c)
        .then(pl.lit("abaixo_da_execucao"))
        .otherwise(pl.lit("acima_da_execucao"))
        .alias("action_status"),
        pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"),
    ).with_columns(gold_period())
    return _conform(frame, AGG_TRANSFER_RECONCILIATION).sort("period", "action_code")


def _status_note(status: str, lens: str) -> str:
    if status == "aberto":
        return "Último mês publicado: a fonte ainda acrescenta lançamentos (parcial)."
    if status == "incompleto":
        return (
            "As transferências deste mês somam menos que o pago na execução da despesa "
            "nas modalidades de transferência: há ações ausentes ou parciais na fonte."
        )
    if lens == LENS_TRANSFERS:
        return "Conferido com a execução da despesa (pago e restos a pagar pagos)."
    if lens == LENS_PAYMENTS:
        return "Mês fechado. Sem conferência com outra base nesta versão."
    return "Mês fechado."


def _complement_note(value: pl.Expr) -> pl.Expr:
    billions = (
        (value.cast(pl.Float64) / 1e9).round(2).cast(pl.String).str.replace(".", ",", literal=True)
    )
    return (
        pl.lit(" Inclui R$ ")
        + billions
        + pl.lit(
            " bi do FPM pela distribuição por município do Tesouro Nacional, ausentes na "
            "fonte (Fonte: Tesouro Nacional, Tesouro Transparente; ODbL)."
        )
    )


def period_status(
    totals: Mapping[str, pl.DataFrame],
    reconciliation: pl.DataFrame,
    *,
    complements: pl.DataFrame | None = None,
    missing_top: int = 5,
) -> pl.DataFrame:
    """Situação de cada mês por lente (ADR-0036, decisão 3).

    ``totals``: lente → (``period`` Gold, ``value``). O último mês de cada lente é
    ``aberto``. Na lente A, um mês com falta acima de ``INCOMPLETE_SHARE`` do pago na lente C
    é ``incompleto``; os demais são ``fechados``. ``complements``: (``period`` Gold,
    ``complement_value``) do FPM pelo Tesouro (ADR-0038), anotado na nota do mês.
    """
    by_period = reconciliation.group_by("period").agg(
        _sum("shortfall"),
        (pl.col("paid_execution") + pl.col("payables_paid_execution"))
        .sum()
        .cast(VALUE_DTYPE)
        .alias("reference_value"),
    )
    missing = (
        reconciliation.filter(pl.col("shortfall").cast(pl.Float64) > 0)
        .sort("shortfall", descending=True)
        .group_by("period", maintain_order=True)
        .agg(pl.col("action_name").head(missing_top).alias("missing_actions"))
    )
    parts = []
    for lens, frame in totals.items():
        latest = frame["period"].max()
        out = frame.with_columns(pl.lit(lens).alias("lens"))
        if lens == LENS_TRANSFERS:
            out = out.join(by_period, on="period", how="left").join(
                missing, on="period", how="left"
            )
            if complements is not None and complements.height:
                out = out.join(complements, on="period", how="left")
            share = pl.col("shortfall").cast(pl.Float64) / pl.col("reference_value").cast(
                pl.Float64
            )
            out = out.with_columns(share.alias("shortfall_share"))
            status = (
                pl.when(pl.col("period") == latest)
                .then(pl.lit("aberto"))
                .when(pl.col("shortfall_share") > INCOMPLETE_SHARE)
                .then(pl.lit("incompleto"))
                .otherwise(pl.lit("fechado"))
            )
        else:
            status = (
                pl.when(pl.col("period") == latest)
                .then(pl.lit("aberto"))
                .otherwise(pl.lit("fechado"))
            )
        out = out.with_columns(status.alias("status"))
        notes = {s: _status_note(s, lens) for s in ("aberto", "incompleto", "fechado")}
        note = pl.col("status").replace_strict(notes, return_dtype=pl.String)
        if "complement_value" in out.columns:
            note = (
                pl.when(pl.col("complement_value").is_not_null())
                .then(note + _complement_note(pl.col("complement_value")))
                .otherwise(note)
            )
        out = out.with_columns(
            note.alias("note"),
            pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"),
        )
        parts.append(out)
    frame = pl.concat(parts, how="diagonal_relaxed")
    return _conform(frame, AGG_CONTAS_PERIOD_STATUS).sort("lens", "period")
