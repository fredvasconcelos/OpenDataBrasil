"""Silver das contas públicas: CGU, Tesouro e cadastro do SIOP (ADR-0030 a 0035, ADR-0038).

Regras que não são óbvias:

* **Nada é deduplicado.** As transferências têm linhas idênticas legítimas (352 em
  2025-10: registros distintos da fonte que coincidem em todas as colunas). A chave técnica
  é ``period`` + ``line_number``, e a contagem de duplicatas vai para o relatório (§9.2).
* **Valor original preservado** em ``*_raw``; o decimal aceita ``,8500`` e ``-,85``, que a
  CGU publica sem o zero à esquerda.
* **Município:** SIAFI→IBGE pela TABMUN (lente A); nome + UF contra os nomes da DTB e da
  TABMUN, com as renomeações oficiais ``(EX-...)`` da própria TABMUN (lente B). O método
  fica registrado por linha (ADR-0032). Sem casamento, a Silver não é escrita.
* **Correções aprovadas:** erros da fonte confirmados pelo mantenedor entram numa lista
  explícita (UF + SIAFI + nome exato → IBGE), nunca por semelhança de nome. A evidência é
  oficial: o valor igual ao centavo numa segunda fonte (ADR-0038).
* **FPM do Tesouro** (ADR-0038): arquivo largo (um ano por coluna) com o código SIAFI;
  vira uma linha por município e mês. "-" é mês sem repasse: não vira linha nem zero.
* **Classe do favorecido** (ADR-0031): pelo formato do código e pela natureza jurídica do
  cadastro PJ; instituições financeiras pela CNAE (bancos e caixas econômicas, 64.2).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import polars as pl

from odb_processing.contas_layout import (
    EXECUTION_COLUMNS,
    EXECUTION_VALUES,
    FPM_MUNICIPALITY_PREFIX,
    LEGAL_ENTITY_COLUMNS,
    PAYMENT_COLUMNS,
    TABMUN_COLUMNS,
    TRANSFER_COLUMNS,
)
from odb_processing.datasus import UF_CODES
from odb_processing.parsers import Lineage, ParseError
from odb_processing.values import VALUE_DTYPE

# Valor da CGU: inteiro opcional, vírgula decimal opcional; ",85" e "-,85" existem.
VALUE_PATTERN = r"^-?(\d+(,\d+)?|,\d+)$"
_MASKED_CPF = r"^\*\*\*\.\d{3}\.\d{3}-\*\*$"


@dataclass(frozen=True, slots=True)
class SourceTable:
    """CSV lido da Bronze, com a contagem independente de registros."""

    frame: pl.DataFrame
    records: int  # contados pelo módulo ``csv`` do Python, para conferir o leitor


# ------------------------------------------------------------------ leitura


def read_source_csv(
    content: bytes,
    columns: Sequence[tuple[str, str]],
    *,
    encoding: str,
    delimiter: str = ";",
    has_header: bool = True,
    name: str = "",
) -> SourceTable:
    """CSV da fonte como texto, renomeado e com ``line_number`` (1 = primeiro registro).

    Todas as colunas ficam ``String``: a tipagem é explícita depois (§9.3). O cabeçalho
    precisa ser exatamente o esperado; os registros são recontados com ``csv`` (que trata
    aspas e quebras de linha dentro dos campos) para conferir o leitor do Polars.
    """
    text = content.decode(encoding).lstrip("﻿")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, None) if has_header else None
    records = sum(1 for _ in reader)
    expected = tuple(h for h, _ in columns)
    if has_header and tuple(header or ()) != expected:
        msg = f"{name}: cabeçalho difere do contrato: {header}"
        raise ParseError(msg)
    frame = pl.read_csv(
        io.BytesIO(text.encode("utf-8")),
        separator=delimiter,
        has_header=has_header,
        new_columns=[target for _, target in columns],
        infer_schema=False,
        quote_char='"',
    )
    if frame.width != len(columns):
        msg = f"{name}: {frame.width} colunas, esperadas {len(columns)}"
        raise ParseError(msg)
    frame = frame.with_row_index("line_number", offset=1).with_columns(
        pl.col("line_number").cast(pl.Int64)
    )
    return SourceTable(frame=frame, records=records)


def decimal_value(column: str) -> pl.Expr:
    """Texto da CGU (``1234,56``, ``,85``, ``-,85``) como ``Decimal(38, 6)``; inválido → nulo."""
    raw = pl.col(column).str.strip_chars()
    fixed = raw.str.replace(r"^(-?),", "${1}0,").str.replace(",", ".", literal=True)
    return (
        pl.when(raw.str.contains(VALUE_PATTERN))
        .then(fixed.cast(VALUE_DTYPE, strict=False))
        .otherwise(None)
    )


def name_key(column: str) -> pl.Expr:
    """Nome normalizado para casar municípios: sem acento, caixa alta, sem apóstrofo/hífen."""
    return (
        pl.col(column)
        .str.strip_chars()
        .str.to_uppercase()
        .str.normalize("NFKD")
        .str.replace_all(r"\p{M}", "")
        .str.replace_all(r"['\u2019`\-]", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def empty_to_null(columns: Sequence[str]) -> list[pl.Expr]:
    """Texto vazio da fonte vira nulo (o original vazio não tem outra leitura)."""
    return [
        pl.when(pl.col(c).str.strip_chars() == "").then(None).otherwise(pl.col(c)).alias(c)
        for c in columns
    ]


# ------------------------------------------------------------------ TABMUN


def parse_tabmun(content: bytes, lineage: Lineage, dataset_id: str) -> SourceTable:
    """TABMUN (SIAFI;CNPJ;nome;UF;IBGE, sem cabeçalho) com o nome antigo ``(EX-...)``."""
    table = read_source_csv(
        content,
        [(c, c) for c in TABMUN_COLUMNS],
        encoding="latin-1",
        has_header=False,
        name="tabmun",
    )
    frame = table.frame.with_columns(
        pl.col("name_source").str.strip_chars(),
        pl.col("uf").str.strip_chars(),
        pl.col("municipality_id").str.strip_chars(),
    ).with_columns(
        pl.col("name_source")
        .str.replace(r"\s*\(EX-[^)]*\)\s*$", "")
        .str.strip_chars()
        .alias("current_name"),
        pl.col("name_source")
        .str.extract(r"\(EX-([^)]*)\)", 1)
        .str.strip_chars()
        .alias("former_name"),
        pl.lit(dataset_id).alias("dataset_id"),
        *lineage.columns(),
    )
    return SourceTable(frame=frame, records=table.records)


# ------------------------------------------------------------------ FPM do Tesouro

FPM_FIRST_YEAR = 1996
# Valor do Tesouro: milhar com ponto e duas casas com vírgula ("1.218.505,53"); negativo
# com sinal ou entre parênteses, como na contabilidade ("(180.529,62)": 2 casos, 2001 e 2004).
BRL_PATTERN = r"^(-?\d{1,3}(\.\d{3})*,\d{2}|\(\d{1,3}(\.\d{3})*,\d{2}\))$"
_ABSENT = ("", "-")


def brl_value(column: str) -> pl.Expr:
    """Texto do Tesouro (``1.218.505,53``, ``(180,00)``) como ``Decimal(38, 6)``; senão nulo."""
    raw = pl.col(column).str.strip_chars()
    signed = raw.str.replace(r"^\((.*)\)$", "-${1}")
    fixed = signed.str.replace_all(".", "", literal=True).str.replace(",", ".", literal=True)
    return (
        pl.when(raw.str.contains(BRL_PATTERN))
        .then(fixed.cast(VALUE_DTYPE, strict=False))
        .otherwise(None)
    )


def parse_fpm_municipality(
    content: bytes, *, encoding: str = "latin-1", name: str = ""
) -> SourceTable:
    """Arquivo "FPM por município" do Tesouro em formato longo: município x ano x mês.

    O cabeçalho são as cinco colunas fixas e anos consecutivos desde 1996 (o arquivo ganha
    uma coluna por exercício). Linhas em branco (o fim do arquivo) são ignoradas. ``-`` é
    mês sem repasse: a célula não vira linha. ``records`` conta, com o módulo ``csv``, as
    células com valor, para conferir o leitor do Polars. ``line_number`` é o registro de
    origem (1 = primeira linha depois do cabeçalho).
    """
    text = content.decode(encoding).lstrip("\ufeff")
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    prefix = [h for h, _ in FPM_MUNICIPALITY_PREFIX]
    header = [h.strip() for h in rows[0]] if rows else []
    years = header[len(prefix) :]
    expected = [str(FPM_FIRST_YEAR + i) for i in range(len(years))]
    if header[: len(prefix)] != prefix or not years or years != expected:
        msg = f"{name}: cabeçalho difere do contrato: {header[:7]} ... {header[-2:]}"
        raise ParseError(msg)
    records = 0
    for number, row in enumerate(rows[1:], start=1):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(header):
            msg = f"{name}: registro {number} com {len(row)} campos, esperados {len(header)}"
            raise ParseError(msg)
        records += sum(1 for cell in row[len(prefix) :] if cell.strip() not in _ABSENT)
    targets = [t for _, t in FPM_MUNICIPALITY_PREFIX]
    wide = pl.read_csv(
        io.BytesIO(text.encode("utf-8")),
        separator=";",
        has_header=True,
        new_columns=[*targets, *years],
        infer_schema=False,
        quote_char='"',
    )
    wide = wide.with_row_index("line_number", offset=1).with_columns(
        pl.col("line_number").cast(pl.Int64)
    )
    filled = [pl.col(c).fill_null("").str.strip_chars() != "" for c in [*targets, *years]]
    frame = (
        wide.filter(pl.any_horizontal(filled))
        .unpivot(
            index=["line_number", *targets],
            on=years,
            variable_name="year",
            value_name="value_raw",
        )
        .with_columns(pl.col("value_raw").str.strip_chars())
        .filter(pl.col("value_raw").is_not_null() & ~pl.col("value_raw").is_in(list(_ABSENT)))
    )
    return SourceTable(frame=frame, records=records)


def fpm_frame(
    table: SourceTable,
    *,
    refs: ContasRefs,
    dataset_id: str,
    lineage: Lineage,
    schema: pl.Schema,
) -> pl.DataFrame:
    """FPM do Tesouro por município e mês, com o município IBGE pela TABMUN (ADR-0032)."""
    texts = [t for _, t in FPM_MUNICIPALITY_PREFIX]
    frame = table.frame.with_columns(pl.col(c).str.strip_chars() for c in texts)
    month = pl.col("month_raw").cast(pl.Int32, strict=False)
    wrong = frame.filter(month.is_null() | ~month.is_between(1, 12))
    if wrong.height:
        msg = f"FPM: mês fora de 1 a 12: {wrong['month_raw'].unique().head(5).to_list()}"
        raise ParseError(msg)
    frame = frame.with_columns(
        (pl.col("year") + month.cast(pl.String).str.zfill(2)).alias("period"),
        brl_value("value_raw").alias("value"),
    )
    frame = resolve_by_siafi(frame, refs.tabmun, refs.names).with_columns(
        pl.lit(dataset_id).alias("dataset_id"),
        pl.lit(refs.label).alias("derivation_refs"),
        *lineage.columns(),
    )
    return _ordered(frame, schema)


# ------------------------------------------------------------------ território


def municipality_names(dtb: pl.DataFrame, tabmun: pl.DataFrame) -> pl.DataFrame:
    """(UF, nome normalizado) → município IBGE, a partir da DTB e da TABMUN.

    Fontes, em ordem de preferência: nome da DTB; nome atual na TABMUN; nome antigo
    ``(EX-...)`` da TABMUN (renomeações oficiais: Augusto Severo → Campo Grande/RN).
    Um mesmo nome apontando para dois municípios da mesma UF é erro, nunca escolha.
    """
    uf_by_code = pl.DataFrame({"uf": list(UF_CODES), "uf_id": list(UF_CODES.values())})
    from_dtb = (
        dtb.join(uf_by_code, on="uf_id")
        .select("uf", name_key("municipality_name").alias("name_key"), "municipality_id")
        .with_columns(pl.lit("nome_uf_dtb").alias("territory_method"))
    )
    from_tabmun = tabmun.select(
        "uf", name_key("current_name").alias("name_key"), "municipality_id"
    ).with_columns(pl.lit("nome_uf_tabmun").alias("territory_method"))
    former = (
        tabmun.filter(pl.col("former_name").is_not_null())
        .select("uf", name_key("former_name").alias("name_key"), "municipality_id")
        .with_columns(pl.lit("nome_antigo_tabmun").alias("territory_method"))
    )
    names = pl.concat([from_dtb, from_tabmun, former]).unique(
        ["uf", "name_key"], keep="first", maintain_order=True
    )
    conflicts = (
        pl.concat([from_dtb, from_tabmun, former])
        .group_by("uf", "name_key")
        .agg(pl.col("municipality_id").n_unique().alias("n"))
        .filter(pl.col("n") > 1)
    )
    if conflicts.height:
        msg = f"nomes de município ambíguos na mesma UF: {conflicts.head(5).rows()}"
        raise ParseError(msg)
    return names


CORRECTION_METHOD = "correcao_aprovada"
_CORRECTION_FIELDS = ("uf", "siafi_code", "source_name", "municipality_id", "reason", "approved")
_CORRECTION_SCHEMA = {
    "uf": pl.String,
    "siafi_municipality_code": pl.String,
    "name_key": pl.String,
    "_fix_ibge": pl.String,
}


def territory_corrections(
    entries: Sequence[Mapping[str, Any]], valid_ids: Sequence[str]
) -> pl.DataFrame:
    """Lista explícita de grafias erradas da fonte, aprovadas pelo mantenedor (ADR-0032).

    Cada entrada casa por **igualdade** de UF, código SIAFI e nome normalizado: nunca por
    semelhança. O destino precisa existir na DTB, e cada chave aponta para um só município.
    """
    rows: list[dict[str, str]] = []
    for entry in entries:
        missing = [k for k in _CORRECTION_FIELDS if not str(entry.get(k, "")).strip()]
        if missing:
            msg = f"correção de território sem {missing}: {dict(entry)}"
            raise ParseError(msg)
        if str(entry["municipality_id"]) not in set(valid_ids):
            msg = f"correção aponta para município fora da DTB: {entry['municipality_id']}"
            raise ParseError(msg)
        rows.append(
            {
                "uf": str(entry["uf"]),
                "siafi_municipality_code": str(entry["siafi_code"]),
                "source_name": str(entry["source_name"]),
                "_fix_ibge": str(entry["municipality_id"]),
            }
        )
    if not rows:
        return pl.DataFrame(schema=_CORRECTION_SCHEMA)
    table = pl.DataFrame(rows).with_columns(name_key("source_name").alias("name_key"))
    table = table.select(list(_CORRECTION_SCHEMA))
    if table.unique(["uf", "siafi_municipality_code", "name_key"]).height != table.height:
        msg = "correções de território repetidas para a mesma UF, SIAFI e nome"
        raise ParseError(msg)
    return table


def resolve_by_siafi(
    frame: pl.DataFrame,
    tabmun: pl.DataFrame,
    names: pl.DataFrame,
    corrections: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Lente A: SIAFI→IBGE pela TABMUN; correção aprovada; nome + UF (ADR-0032).

    A correção só vale para um SIAFI ausente da TABMUN: o código oficial sempre vence.
    """
    by_siafi = tabmun.select(
        pl.col("siafi_code").alias("siafi_municipality_code"),
        pl.col("municipality_id").alias("_siafi_ibge"),
    )
    fixes = corrections if corrections is not None else pl.DataFrame(schema=_CORRECTION_SCHEMA)
    out = (
        frame.join(by_siafi, on="siafi_municipality_code", how="left")
        .with_columns(name_key("municipality_name_source").alias("name_key"))
        .join(fixes, on=["uf", "siafi_municipality_code", "name_key"], how="left")
        .join(
            names.rename({"municipality_id": "_name_ibge", "territory_method": "_name_method"}),
            on=["uf", "name_key"],
            how="left",
        )
    )
    code = pl.col("siafi_municipality_code")
    no_municipality = code.is_null() | (code == "")
    resolved = pl.coalesce("_siafi_ibge", "_fix_ibge", "_name_ibge")
    return out.with_columns(
        pl.when(no_municipality).then(None).otherwise(resolved).alias("municipality_id"),
        pl.when(no_municipality)
        .then(pl.lit("sem_municipio"))
        .when(code == "-14")
        .then(pl.lit("multiplo"))
        .when(resolved.is_not_null())
        .then(pl.lit("municipio"))
        .otherwise(pl.lit("nao_resolvido"))
        .alias("territory_status"),
        pl.when(no_municipality | (code == "-14"))
        .then(None)
        .when(pl.col("_siafi_ibge").is_not_null())
        .then(pl.lit("tabmun_siafi"))
        .when(pl.col("_fix_ibge").is_not_null())
        .then(pl.lit(CORRECTION_METHOD))
        .otherwise(pl.col("_name_method"))
        .alias("territory_method"),
    ).drop("_siafi_ibge", "_fix_ibge", "_name_ibge", "_name_method", "name_key")


def resolve_by_name(frame: pl.DataFrame, names: pl.DataFrame) -> pl.DataFrame:
    """Lente B: UF + nome da sede contra a união de DTB e TABMUN.

    ``EX`` (exterior) e ``-1`` (sem informação) são estados próprios, sem município.
    """
    out = frame.with_columns(name_key("municipality_name_source").alias("name_key")).join(
        names.rename({"territory_method": "_method"}), on=["uf", "name_key"], how="left"
    )
    uf = pl.col("uf")
    return (
        out.with_columns(
            pl.when(uf == "EX")
            .then(pl.lit("exterior"))
            .when((uf == "-1") | uf.is_null())
            .then(pl.lit("sem_informacao"))
            .when(pl.col("municipality_id").is_not_null())
            .then(pl.lit("municipio"))
            .otherwise(pl.lit("nao_resolvido"))
            .alias("territory_status"),
            pl.when(uf.is_in(["EX", "-1"]))
            .then(None)
            .otherwise(pl.col("_method"))
            .alias("territory_method"),
        )
        .with_columns(
            pl.when(pl.col("territory_status") == "municipio")
            .then(pl.col("municipality_id"))
            .otherwise(None)
            .alias("municipality_id")
        )
        .drop("_method", "name_key")
    )


# ------------------------------------------------------------------ classe do favorecido

# Natureza jurídica (tabela do cadastro PJ da CGU, Receita/CONCLA).
_MUNICIPAL_FUND = ("1333", "1309")
_STATE_FUND = ("1325", "1295")
_FEDERAL_FUND = ("1317", "1287")


def recipient_class(code: str = "recipient_code") -> pl.Expr:
    """Classe do favorecido (ADR-0031), versão ``RECIPIENT_CLASS_VERSION``.

    Códigos negativos são marcas da fonte: ``-11`` sigiloso; os demais (``-1`` sem
    informação, ``-3`` inválido, ``-8`` sem informação, ``-9`` não se aplica, vistos nas
    transferências de 2024 a 2026) ficam como ``sem_informacao``, com o código original.

    Precisa das colunas ``legal_nature_code``, ``cnae_code`` e ``is_prefecture`` (CNPJ da
    prefeitura na TABMUN), obtidas do cadastro PJ e da TABMUN.
    """
    c = pl.col(code)
    nature = pl.col("legal_nature_code")
    cnae = pl.col("cnae_code")
    return (
        pl.when(c.str.contains(r"^(TN|RB)"))
        .then(pl.lit("lancamento_agregado"))
        .when(c.str.contains(r"^\d{6}$"))
        .then(pl.lit("unidade_gestora_federal"))
        .when(c == "-11")
        .then(pl.lit("sigiloso"))
        .when(c.str.contains(r"^-\d+$"))
        .then(pl.lit("sem_informacao"))
        .when(c.str.starts_with("EX"))
        .then(pl.lit("exterior"))
        .when(c.str.contains(_MASKED_CPF))
        .then(pl.lit("pessoa_fisica"))
        .when(c.str.starts_with("PF"))
        .then(pl.lit("pessoa_fisica_sem_cpf"))
        .when(pl.col("is_prefecture") | (nature == "1244"))
        .then(pl.lit("municipio"))
        .when(nature == "1236")
        .then(pl.lit("estado_df"))
        .when(nature.is_in(_MUNICIPAL_FUND))
        .then(pl.lit("fundo_municipal"))
        .when(nature.is_in(_STATE_FUND))
        .then(pl.lit("fundo_estadual"))
        .when(nature.is_in(_FEDERAL_FUND))
        .then(pl.lit("fundo_federal"))
        # Bancos e caixas econômicas (CNAE 64.2): agentes pagadores de folha, consignado e
        # benefícios na lente B; a classe permite separá-los dos destinatários.
        .when(cnae.str.starts_with("642"))
        .then(pl.lit("instituicao_financeira"))
        .when(nature.str.starts_with("1"))
        .then(pl.lit("outro_ente_publico"))
        .when(nature.str.starts_with("2"))
        .then(pl.lit("empresa"))
        .when(nature.str.starts_with("3"))
        .then(pl.lit("entidade_sem_fins_lucrativos"))
        .when(nature.str.starts_with("4"))
        .then(pl.lit("pessoa_fisica_com_cnpj"))
        .when(nature.str.starts_with("5"))
        .then(pl.lit("organizacao_internacional"))
        .otherwise(pl.lit("nao_classificado"))
    )


RECIPIENT_CLASS_VERSION = "1.1.0"  # 1.1.0: todos os códigos negativos da fonte


def with_recipient_class(
    frame: pl.DataFrame, legal_entities: pl.DataFrame, tabmun: pl.DataFrame
) -> pl.DataFrame:
    """Acrescenta natureza jurídica, CNAE e ``recipient_class`` ao quadro."""
    entities = legal_entities.select("recipient_code", "legal_nature_code", "cnae_code")
    prefectures = (
        tabmun.select(pl.col("prefecture_cnpj").alias("recipient_code"))
        .with_columns(pl.lit(value=True).alias("is_prefecture"))
        .unique("recipient_code")
    )
    return (
        frame.join(entities, on="recipient_code", how="left")
        .join(prefectures, on="recipient_code", how="left")
        .with_columns(pl.col("is_prefecture").fill_null(value=False))
        .with_columns(recipient_class().alias("recipient_class"))
        .drop("is_prefecture", "cnae_code")
    )


# ------------------------------------------------------------------ período


def period_from_raw(raw: str, kind: str) -> pl.Expr:
    """``AAAAMM`` a partir de ``202510`` (transferências), ``10/2025`` ou ``2025/10``."""
    c = pl.col(raw).str.strip_chars()
    if kind == "aaaamm":
        return c
    if kind == "mm/aaaa":
        return c.str.slice(3, 4) + c.str.slice(0, 2)
    if kind == "aaaa/mm":
        return c.str.slice(0, 4) + c.str.slice(5, 2)
    msg = f"formato de período desconhecido: {kind}"
    raise ValueError(msg)


def full_row_duplicates(frame: pl.DataFrame, columns: Sequence[str]) -> int:
    """Linhas idênticas em todas as colunas da fonte (informativo; nada é removido)."""
    return int(frame.select(columns).is_duplicated().sum())


# ------------------------------------------------------------------ referências


@dataclass(frozen=True, slots=True)
class ContasRefs:
    """Referências Silver usadas na derivação de território e classe."""

    tabmun: pl.DataFrame  # siafi_municipality vigente
    names: pl.DataFrame  # municipality_names(DTB, TABMUN)
    legal_entities: pl.DataFrame  # cgu_legal_entity, instantâneo mais recente
    label: str  # ex.: "ibge-dtb@v1;tesouro-tabmun@v2;cgu-favorecidos-pj@v1"
    corrections: pl.DataFrame = field(
        default_factory=lambda: pl.DataFrame(schema=_CORRECTION_SCHEMA)
    )  # territory_corrections() do dataset


# ------------------------------------------------------------------ lentes (mensais)


def _ordered(frame: pl.DataFrame, schema: pl.Schema) -> pl.DataFrame:
    return frame.select([pl.col(name).cast(dtype) for name, dtype in schema.items()])


def transfer_frame(
    table: SourceTable, *, period: str, refs: ContasRefs, lineage: Lineage, schema: pl.Schema
) -> pl.DataFrame:
    """Lente A (Recursos transferidos) de um mês."""
    names = [n for _, n in TRANSFER_COLUMNS]
    frame = table.frame.with_columns(empty_to_null(names))
    frame = resolve_by_siafi(frame, refs.tabmun, refs.names, refs.corrections)
    frame = with_recipient_class(frame, refs.legal_entities, refs.tabmun)
    frame = frame.with_columns(
        pl.lit(period).alias("period"),
        decimal_value("value_raw").alias("value"),
        pl.lit(RECIPIENT_CLASS_VERSION).alias("recipient_class_version"),
        pl.lit(refs.label).alias("derivation_refs"),
        *lineage.columns(),
    )
    return _ordered(frame, schema)


def payment_frame(
    table: SourceTable, *, period: str, refs: ContasRefs, lineage: Lineage, schema: pl.Schema
) -> pl.DataFrame:
    """Lente B (Recebimento de recursos por favorecido) de um mês."""
    names = [n for _, n in PAYMENT_COLUMNS]
    frame = table.frame.with_columns(empty_to_null(names))
    frame = resolve_by_name(frame, refs.names)
    frame = with_recipient_class(frame, refs.legal_entities, refs.tabmun)
    frame = frame.with_columns(
        pl.lit(period).alias("period"),
        decimal_value("value_raw").alias("value"),
        pl.lit(RECIPIENT_CLASS_VERSION).alias("recipient_class_version"),
        pl.lit(refs.label).alias("derivation_refs"),
        *lineage.columns(),
    )
    return _ordered(frame, schema)


def execution_frame(
    table: SourceTable, *, period: str, lineage: Lineage, schema: pl.Schema
) -> pl.DataFrame:
    """Lente C (Execução da despesa) de um mês; o localizador fica como na fonte."""
    names = [n for _, n in EXECUTION_COLUMNS]
    frame = table.frame.with_columns(empty_to_null(names)).with_columns(
        pl.lit(period).alias("period"),
        *(decimal_value(f"{name}_raw").alias(name) for _, name in EXECUTION_VALUES),
        *lineage.columns(),
    )
    return _ordered(frame, schema)


# ------------------------------------------------------------------ cadastros


def legal_entity_frame(
    entities: SourceTable,
    cnae: SourceTable,
    natures: SourceTable,
    *,
    snapshot: str,
    lineage: Lineage,
    schema: pl.Schema,
) -> pl.DataFrame:
    """Cadastro PJ com as descrições de CNAE e natureza jurídica (códigos ``0…`` sem descrição)."""
    names = [n for _, n in LEGAL_ENTITY_COLUMNS]
    frame = (
        entities.frame.with_columns(empty_to_null(names))
        .join(cnae.frame.drop("line_number"), on="cnae_code", how="left")
        .join(natures.frame.drop("line_number"), on="legal_nature_code", how="left")
        .with_columns(pl.lit(snapshot).alias("snapshot"), *lineage.columns())
    )
    return _ordered(frame, schema)


def siop_frame(
    table: SourceTable,
    columns: Sequence[tuple[str, str]],
    *,
    lineage: Lineage,
    schema: pl.Schema,
) -> pl.DataFrame:
    """Cadastro do SIOP (ações ou planos orçamentários): texto oficial, sem edição."""
    text = [n for _, n in columns]
    frame = table.frame.with_columns(empty_to_null(text)).with_columns(*lineage.columns())
    return _ordered(frame, schema)


def tabmun_frame(table: SourceTable, *, schema: pl.Schema) -> pl.DataFrame:
    """TABMUN na ordem do contrato."""
    return _ordered(table.frame, schema)
