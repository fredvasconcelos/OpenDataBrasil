"""SINESP VDE (Ministério da Justiça e Segurança Pública) → observações na Silver.

A base anual ``bancovde-AAAA.xlsx`` traz uma linha por UF, município, evento, mês e
(quando o evento tem) agente, arma ou faixa etária, com as contagens publicadas pelos
gestores estaduais e pelas polícias federais (``abrangencia``). Cada evento usa uma
medida: ``total`` (ocorrências, apreensões, mandados), ``total_vitima`` (vítimas, com
``feminino``/``masculino``/``nao_informado``) ou ``total_peso`` (kg de droga apreendida).

Desenho da Silver (ADR-0012), no contrato de observação do SIDRA:

* uma variável por evento e medida, com a unidade da medida publicada;
* município (nível 6) quando a linha traz um município que casa com a DTB pelo nome e
  pela UF; UF (nível 3) com a soma de todas as linhas da UF, inclusive "NÃO INFORMADO"
  e municípios sem correspondência (registrados no relatório); Brasil (nível 1),
  derivado: soma das UFs, ausente no mês em que qualquer parcela falta (a fonte não
  publica o total nacional);
* Total e a distribuição de cada dimensão presente no evento (abrangência, sexo,
  agente, arma, faixa etária), com as demais no Total, sem cruzamento (como o SIM);
* linhas repetidas da mesma chave são somadas (nota oficial da página de download);
* valor ausente na fonte → "..." (não disponível); total com parcela ausente também;
  zero informado → zero verdadeiro (as notas dos gestores mostram zeros que significam
  "indisponível": ver ADR-0012, decisão 6).
"""

from __future__ import annotations

import hashlib
import re
import tomllib
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from odb_processing.contracts import SIDRA_OBSERVATION
from odb_processing.parsers import Lineage, ParseError
from odb_processing.values import ValueStatus, classify_sidra_values

TOTAL = "T"
NOT_INFORMED = "NÃO INFORMADO"
MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip

# Colunas da planilha oficial (verificadas em bancovde-2023.xlsx, 2026-11-12).
COLUMNS = {
    "uf": pl.String,
    "municipio": pl.String,
    "evento": pl.String,
    "data_referencia": pl.Date,
    "agente": pl.String,
    "arma": pl.String,
    "faixa_etaria": pl.String,
    "feminino": pl.Int64,
    "masculino": pl.Int64,
    "nao_informado": pl.Int64,
    "total_vitima": pl.Int64,
    "total": pl.Int64,
    "total_peso": pl.String,
    "abrangencia": pl.String,
}
# Unidade de ``total`` por evento quando não é "Ocorrências" (contagem publicada).
COUNT_UNITS = {
    "Arma de Fogo Apreendida": "Armas",
    "Mandado de prisão cumprido": "Mandados",
    "Emissão de Alvarás de licença": "Alvarás",
    "Realização de vistorias": "Vistorias",
    "Atendimento pré-hospitalar": "Atendimentos",
}
# Dimensões em linha (uma coluna da planilha) e a dimensão de sexo (colunas de vítimas).
ROW_DIMENSIONS = (
    ("abrangencia", "Abrangência"),
    ("agente", "Agente"),
    ("arma", "Arma"),
    ("faixa_etaria", "Faixa etária"),
)
SEX = (("feminino", "Feminino"), ("masculino", "Masculino"), ("nao_informado", "Não informado"))


def normalize_name(name: str) -> str:
    """Nome de município comparável: sem acentos, maiúsculo, sem apóstrofo e hífen."""
    text = unicodedata.normalize("NFD", name)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").upper()
    text = re.sub("['`\u2019\u00b4]", "", text)  # apóstrofos e acentos soltos
    text = re.sub("[-\u2013]", " ", text)  # hífen e meia-risca
    return re.sub(r"\s+", " ", text).strip()


def slug(text: str) -> str:
    """Identificador estável da variável a partir do nome do evento."""
    return re.sub(r"[^a-z0-9]+", "-", normalize_name(text).lower()).strip("-")


@dataclass(frozen=True)
class Unavailable:
    """Período que o gestor estadual declara indisponível (tabela de cobertura, ADR-0012)."""

    uf: str
    events: tuple[str, ...]
    start: str  # AAAAMM, inclusive
    end: str  # AAAAMM, inclusive
    source: str

    @property
    def label(self) -> str:
        return f"{self.uf} {self.start}-{self.end}: {', '.join(self.events)}"


def load_coverage(path: Path) -> tuple[list[Unavailable], str]:
    """Lê a tabela de cobertura e devolve as entradas e o SHA-256 do arquivo."""
    content = path.read_bytes()
    data = tomllib.loads(content.decode("utf-8"))
    entries = []
    for item in data.get("unavailable", []):
        entry = Unavailable(
            uf=str(item["uf"]),
            events=tuple(str(e) for e in item["events"]),
            start=str(item["start"]),
            end=str(item["end"]),
            source=str(item["source"]),
        )
        if not (re.fullmatch(r"\d{6}", entry.start) and re.fullmatch(r"\d{6}", entry.end)):
            msg = f"cobertura com período fora de AAAAMM: {entry.label}"
            raise ParseError(msg)
        if entry.start > entry.end:
            msg = f"cobertura com início depois do fim: {entry.label}"
            raise ParseError(msg)
        entries.append(entry)
    return entries, hashlib.sha256(content).hexdigest()


@dataclass
class VdeReport:
    """O que a conversão encontrou e merece atenção (vai para as verificações)."""

    rows: int = 0
    duplicated_keys: int = 0
    unmatched: dict[str, int] = field(default_factory=dict)  # "UF/NOME" → linhas
    events: dict[str, str] = field(default_factory=dict)  # evento → medida
    # Séries federais (PF/PRF) vazias no ano inteiro, por UF: "não se aplica", fora da soma.
    federal_empty: dict[str, list[str]] = field(default_factory=dict)  # evento → UFs
    # Tabela de cobertura: linhas estaduais marcadas indisponíveis, por entrada; e eventos
    # citados na tabela que não existem na planilha (erro de digitação ou evento extinto).
    coverage_applied: dict[str, int] = field(default_factory=dict)
    coverage_unknown_events: list[str] = field(default_factory=list)


def read_vde(path: Path) -> pl.DataFrame:
    """Lê a planilha anual (primeira aba) com os tipos esperados."""
    frame = pl.read_excel(path, schema_overrides=COLUMNS)
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        msg = f"colunas ausentes na planilha do SINESP VDE: {sorted(missing)}"
        raise ParseError(msg)
    return frame.select(list(COLUMNS)).cast(COLUMNS)  # type: ignore[arg-type]


def _measure(frame: pl.DataFrame) -> dict[str, str]:
    """Medida usada por evento: a coluna preenchida (vítimas, peso ou total)."""
    used = frame.group_by("evento").agg(
        pl.col("total_vitima").is_not_null().any().alias("vitima"),
        pl.col("total_peso").is_not_null().any().alias("peso"),
    )
    return {
        str(r["evento"]): "vitima" if r["vitima"] else "peso" if r["peso"] else "total"
        for r in used.iter_rows(named=True)
    }


def _sum_or_null(column: str) -> pl.Expr:
    """Soma do grupo, ou ausente se qualquer parcela for ausente.

    Um total com parcela faltando seria um número incompleto apresentado como completo
    (ex.: apreensão no Tocantins com a parte estadual vazia e a da PF zerada). Ausência
    nunca vira zero (§9.4).
    """
    return (
        pl.when(pl.col(column).is_null().any())
        .then(pl.lit(None))
        .otherwise(pl.col(column).sum())
        .alias(column)
    )


def sinesp_observations(
    raw: pl.DataFrame,
    *,
    year: str,
    uf_codes: Mapping[str, str],
    municipalities: Mapping[tuple[str, str], str],
    table_id: str,
    lineage: Lineage,
    unavailable: Sequence[Unavailable] = (),
) -> tuple[pl.DataFrame, VdeReport]:
    """Planilha de um ano → observações (contrato ``sidra_observation``).

    ``municipalities``: (sigla da UF, nome normalizado) → código IBGE de 7 dígitos.
    ``unavailable``: tabela de cobertura; as linhas estaduais desses períodos viram
    ausentes antes da soma (o zero publicado não é contagem).
    """
    report = VdeReport(rows=raw.height)
    unknown = set(raw["uf"].drop_nulls().unique()) - set(uf_codes)
    if unknown:
        msg = f"UF desconhecida no SINESP VDE: {sorted(unknown)}"
        raise ParseError(msg)
    years = raw["data_referencia"].dt.year().unique().to_list()
    if years != [int(year)]:
        msg = f"planilha de {year} com datas de outros anos: {sorted(years)}"
        raise ParseError(msg)
    measures = _measure(raw)
    report.events = dict(sorted(measures.items()))

    names = {f"{uf}/{name}": code for (uf, name), code in municipalities.items()}
    frame = raw.with_columns(
        pl.col("data_referencia").dt.strftime("%Y%m").alias("period"),
        pl.col("uf").replace_strict(uf_codes).alias("uf_code"),
        pl.col("evento").replace_strict(measures).alias("measure"),
        (
            pl.col("uf")
            + pl.lit("/")
            + pl.col("municipio").map_elements(normalize_name, return_dtype=pl.String)
        )
        .replace_strict(names, default=None)
        .alias("municipality_id"),
        pl.col("total_peso").str.strip_chars().cast(pl.Float64, strict=False).alias("peso"),
    )
    keys = ["uf", "municipio", "evento", "data_referencia", "agente", "arma", "faixa_etaria"]
    report.duplicated_keys = (
        frame.group_by([*keys, "abrangencia"]).len().filter(pl.col("len") > 1).height
    )
    missing = frame.filter(
        pl.col("municipality_id").is_null() & (pl.col("municipio") != NOT_INFORMED)
    )
    report.unmatched = {
        f"{r['uf']}/{r['municipio']}": int(r["len"])
        for r in missing.group_by("uf", "municipio")
        .len()
        .sort("uf", "municipio")
        .iter_rows(named=True)
    }

    # Valor por linha na medida do evento e, para vítimas, as colunas de sexo.
    value = (
        pl.when(pl.col("measure") == "vitima")
        .then(pl.col("total_vitima").cast(pl.Float64))
        .when(pl.col("measure") == "peso")
        .then(pl.col("peso"))
        .otherwise(pl.col("total").cast(pl.Float64))
    )
    base = frame.with_columns(value.alias("v"), *[pl.col(c).cast(pl.Float64) for c, _ in SEX])
    base = _apply_coverage(base, unavailable, report)
    # Série federal sempre vazia na UF e no evento (ex.: PF em roubo de veículo): a
    # polícia federal não informa o evento ali. Sai da soma; a estadual vazia não sai
    # (dado indisponível deixa o total ausente).
    empty = (
        base.filter(pl.col("abrangencia") != "Estadual")
        .group_by("uf", "evento", "abrangencia")
        .agg(pl.col("v").is_null().all().alias("empty"))
        .filter(pl.col("empty"))
        .drop("empty")
    )
    report.federal_empty = {
        str(r["evento"]): sorted(r["uf"])
        for r in empty.group_by("evento").agg(pl.col("uf").unique()).iter_rows(named=True)
    }
    base = base.join(empty, on=["uf", "evento", "abrangencia"], how="anti")
    dims_by_event = _dimensions_of(base)
    with_dim = {
        label: [e for e, labels in dims_by_event.items() if label in labels]
        for _, label in (*ROW_DIMENSIONS, ("", "Sexo"))
    }

    parts = []
    territories = (
        ("6", pl.col("municipality_id")),
        ("3", pl.col("uf_code")),
        ("1", pl.lit("1")),  # Brasil: soma estrita de todas as linhas (derivado)
    )
    for level, territory in territories:
        located = base.with_columns(territory.alias("territory_id")).drop_nulls("territory_id")
        group = ["territory_id", "evento", "measure", "period"]
        # Total (todas as dimensões no Total).
        parts.append(
            located.group_by(group)
            .agg(_sum_or_null("v"))
            .with_columns(
                pl.lit(level).alias("territorial_level"),
                pl.lit(None, dtype=pl.String).alias("dim_label"),
                pl.lit(None, dtype=pl.String).alias("dim_value"),
            )
        )
        # Cada dimensão em linha, só nos eventos em que ela entra (``_dimensions_of``).
        for column, label in ROW_DIMENSIONS:
            present = located.filter(
                pl.col("evento").is_in(with_dim[label]) & pl.col(column).is_not_null()
            )
            parts.append(
                present.group_by([*group, column])
                .agg(_sum_or_null("v"))
                .with_columns(
                    pl.lit(level).alias("territorial_level"),
                    pl.lit(label).alias("dim_label"),
                    pl.col(column).alias("dim_value"),
                )
            )
        # Sexo das vítimas (colunas da planilha).
        victims = located.filter(pl.col("evento").is_in(with_dim["Sexo"]))
        for column, label in SEX:
            parts.append(
                victims.group_by(group)
                .agg(_sum_or_null(column).alias("v"))
                .with_columns(
                    pl.lit(level).alias("territorial_level"),
                    pl.lit("Sexo").alias("dim_label"),
                    pl.lit(label).alias("dim_value"),
                )
            )
    columns = [
        "territory_id", "evento", "measure", "period", "v",
        "territorial_level", "dim_label", "dim_value",
    ]  # fmt: skip
    agg = pl.concat([p.select(columns) for p in parts])
    return _to_contract(agg, dims_by_event, table_id=table_id, lineage=lineage), report


def _apply_coverage(
    base: pl.DataFrame, unavailable: Sequence[Unavailable], report: VdeReport
) -> pl.DataFrame:
    """Marca como ausentes as linhas estaduais dos períodos declarados indisponíveis."""
    if not unavailable:
        return base
    known = set(base["evento"].unique().to_list())
    report.coverage_unknown_events = sorted(
        {e for entry in unavailable for e in entry.events} - known
    )
    mask = pl.lit(value=False)
    for entry in unavailable:
        hit = (
            (pl.col("uf") == entry.uf)
            & pl.col("evento").is_in(list(entry.events))
            & pl.col("period").is_between(pl.lit(entry.start), pl.lit(entry.end))
            & (pl.col("abrangencia") == "Estadual")
        )
        count = base.select(hit.sum()).item()
        if count:
            report.coverage_applied[entry.label] = int(count)
        mask = mask | hit
    columns = ["v", *(c for c, _ in SEX)]
    return base.with_columns(
        [
            pl.when(mask).then(pl.lit(None, dtype=pl.Float64)).otherwise(pl.col(c)).alias(c)
            for c in columns
        ]
    )


def _dimensions_of(frame: pl.DataFrame) -> dict[str, list[str]]:
    """Dimensões de cada evento (as classificações da observação).

    Agente, arma e faixa etária entram quando preenchidas no evento. A abrangência só
    entra quando o evento tem linhas da PF ou da PRF; com só "Estadual", ela repetiria
    o Total.
    """
    out: dict[str, list[str]] = {}
    for event, part in frame.partition_by("evento", as_dict=True).items():
        dims = [
            label
            for column, label in ROW_DIMENSIONS
            if (
                (part[column] != "Estadual").any()
                if column == "abrangencia"
                else part[column].is_not_null().any()
            )
        ]
        if (part["measure"] == "vitima").any():
            dims.append("Sexo")
        out[str(event[0])] = dims
    return out


def _to_contract(
    agg: pl.DataFrame,
    dims_by_event: Mapping[str, list[str]],
    *,
    table_id: str,
    lineage: Lineage,
) -> pl.DataFrame:
    rows = []
    # Código da categoria: o nome sem acento nem espaço ("Não informado" → "nao-informado"),
    # no formato que o catálogo e a API aceitam; o nome publicado fica em category_name.
    codes = {v: slug(v) for v in agg["dim_value"].drop_nulls().unique().to_list()}
    for event, labels in dims_by_event.items():
        part = agg.filter(pl.col("evento") == event)

        def category(label: str) -> pl.Expr:
            return (
                pl.when(pl.col("dim_label") == label)
                .then(pl.col("dim_value").replace_strict(codes, default=None))
                .otherwise(pl.lit(TOTAL))
            )

        def category_name(label: str) -> pl.Expr:
            return (
                pl.when(pl.col("dim_label") == label)
                .then(pl.col("dim_value"))
                .otherwise(pl.lit("Total"))
            )

        structs = [
            pl.struct(
                pl.lit(label).alias("dimension"),
                category(label).alias("category_id"),
                category_name(label).alias("category_name"),
            )
            for label in labels
        ]
        key = (
            pl.concat_str(
                [pl.lit(f"{label}=") + category(label) for label in labels], separator=";"
            )
            if labels
            else pl.lit("")
        )
        classifications = (
            pl.concat_list(structs)
            if structs
            else pl.lit([], dtype=SIDRA_OBSERVATION.schema["classifications"])
        )
        rows.append(
            part.with_columns(
                key.alias("classification_key"), classifications.alias("classifications")
            )
        )
    out = pl.concat(rows)
    unit = (
        pl.when(pl.col("measure") == "vitima")
        .then(pl.lit("Vítimas"))
        .when(pl.col("measure") == "peso")
        .then(pl.lit("Quilogramas"))
        .otherwise(pl.col("evento").replace_strict(COUNT_UNITS, default="Ocorrências"))
    )
    month = pl.col("period").str.slice(4, 2).cast(pl.Int32)
    value_raw = (
        pl.when(pl.col("v").is_null())
        .then(pl.lit("..."))
        .when(pl.col("measure") == "peso")
        .then(pl.col("v").round(3).cast(pl.String))
        .otherwise(pl.col("v").cast(pl.Int64).cast(pl.String))
    )
    result = (
        out.select(
            pl.lit(table_id).alias("table_id"),
            (pl.col("evento").map_elements(slug, return_dtype=pl.String)).alias("variable_id"),
            pl.col("evento").alias("variable_name"),
            unit.map_elements(slug, return_dtype=pl.String).alias("unit_id"),
            unit.alias("unit_name"),
            pl.col("territorial_level"),
            pl.col("territorial_level")
            .replace_strict({"6": "Município", "3": "Unidade da Federação", "1": "Brasil"})
            .alias("territorial_level_name"),
            pl.col("territory_id"),
            pl.lit(None, dtype=pl.String).alias("territory_name"),
            pl.col("period"),
            (
                month.replace_strict(dict(enumerate(MONTHS, start=1)), return_dtype=pl.String)
                + pl.lit(" ")
                + pl.col("period").str.slice(0, 4)
            ).alias("period_name"),
            pl.col("classification_key"),
            pl.col("classifications"),
            value_raw.alias("value_raw"),
        )
        .with_columns(*classify_sidra_values(), *lineage.columns())
        # Zero informado pelo gestor é contagem, não arredondamento (legenda do SIDRA).
        .with_columns(
            pl.when(pl.col("value_status") == ValueStatus.ROUNDED_ZERO.value)
            .then(pl.lit(ValueStatus.TRUE_ZERO.value))
            .otherwise(pl.col("value_status"))
            .alias("value_status")
        )
    )
    return result.select(SIDRA_OBSERVATION.frame_schema().names()).cast(
        SIDRA_OBSERVATION.frame_schema()
    )
