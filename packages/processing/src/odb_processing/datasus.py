"""Microdados do DATASUS (``.dbc``) → agregados por município na Silver.

A unidade mínima do projeto é o município (decisão do mantenedor, 2026-11-11):
os registros individuais ficam só na Bronze, e a Silver guarda contagens por
município de residência, ano e dimensões. O formato é o contrato de observação
da Silver (``sidra_observation``), o mesmo das tabelas do SIDRA, para que a Gold
e a comparação com o Registro Civil do IBGE usem a mesma estrutura.

Cada arquivo do SIM (``DO<UF><ano>.dbc``, uma UF de residência num ano) gera:

* nível 6 (município): óbitos por município de residência, com o código de 6
  dígitos do DATASUS convertido no código IBGE de 7 dígitos pela DTB;
* nível 3 (UF): todos os óbitos do arquivo, inclusive os de município ignorado
  ou sem correspondência na DTB (por isso a soma dos municípios pode ser menor
  que a UF).

Em cada território há o Total e a distribuição de cada dimensão com as demais
no Total (desenho das tabelas do SIDRA). As dimensões não são cruzadas entre
si: o cruzamento completo manteria quase um registro por óbito (risco de
reidentificação em municípios pequenos, §23) e não serve ao panorama.

A soma das contagens de cada nível é conferida contra o número de registros
lidos (nada se perde na agregação).

Codificação (estrutura do SIM, ``SIM/CID10/DOCS`` no FTP):

* ``IDADE``: 3 dígitos; o primeiro é a unidade (0 minutos, 1 horas, 2 dias,
  3 meses, 4 anos, 5 anos acima de 100) e os dois últimos, a quantidade;
* ``CAUSABAS``: causa básica na CID-10 (letra e dígitos), agrupada em capítulos;
* ``SEXO`` (1/M masculino, 2/F feminino), ``RACACOR`` (1 a 5) e ``LOCOCOR``
  (1 a 6); outros valores e vazios viram "Ignorado".
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import polars as pl

from odb_processing.contracts import SIDRA_OBSERVATION
from odb_processing.parsers import Lineage, ParseError
from odb_processing.values import classify_sidra_values

SIM_FIELDS = ("DTOBITO", "CODMUNRES", "SEXO", "IDADE", "RACACOR", "CAUSABAS", "LOCOCOR")

UF_CODES = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}  # fmt: skip

SEX = {"1": "Masculino", "M": "Masculino", "2": "Feminino", "F": "Feminino"}
RACE = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indígena"}
PLACE = {
    "1": "Hospital",
    "2": "Outro estabelecimento de saúde",
    "3": "Domicílio",
    "4": "Via pública",
    "5": "Outros",
    "6": "Aldeia indígena",
}
IGNORED = ("9", "Ignorado")

# Capítulos da CID-10: (primeiro código, último código, número romano, nome).
CID10_CHAPTERS = (
    ("A00", "B99", "I", "Algumas doenças infecciosas e parasitárias"),
    ("C00", "D48", "II", "Neoplasias (tumores)"),
    (
        "D50",
        "D89",
        "III",
        "Doenças do sangue e dos órgãos hematopoéticos e transtornos imunitários",
    ),
    ("E00", "E90", "IV", "Doenças endócrinas, nutricionais e metabólicas"),
    ("F00", "F99", "V", "Transtornos mentais e comportamentais"),
    ("G00", "G99", "VI", "Doenças do sistema nervoso"),
    ("H00", "H59", "VII", "Doenças do olho e anexos"),
    ("H60", "H95", "VIII", "Doenças do ouvido e da apófise mastoide"),
    ("I00", "I99", "IX", "Doenças do aparelho circulatório"),
    ("J00", "J99", "X", "Doenças do aparelho respiratório"),
    ("K00", "K93", "XI", "Doenças do aparelho digestivo"),
    ("L00", "L99", "XII", "Doenças da pele e do tecido subcutâneo"),
    ("M00", "M99", "XIII", "Doenças do sistema osteomuscular e do tecido conjuntivo"),
    ("N00", "N99", "XIV", "Doenças do aparelho geniturinário"),
    ("O00", "O99", "XV", "Gravidez, parto e puerpério"),
    ("P00", "P96", "XVI", "Algumas afecções originadas no período perinatal"),
    ("Q00", "Q99", "XVII", "Malformações congênitas, deformidades e anomalias cromossômicas"),
    ("R00", "R99", "XVIII", "Sintomas, sinais e achados anormais (causas mal definidas)"),
    ("S00", "T98", "XIX", "Lesões, envenenamentos e outras consequências de causas externas"),
    ("V01", "Y98", "XX", "Causas externas de morbidade e de mortalidade"),
    ("Z00", "Z99", "XXI", "Fatores que influenciam o estado de saúde"),
    ("U00", "U99", "XXII", "Códigos para propósitos especiais"),
)

# Faixas etárias (anos): id = limite inferior; a última é aberta.
AGE_GROUPS = (
    (0, 0, "0", "Menor de 1 ano"),
    (1, 4, "1", "1 a 4 anos"),
    *((lo, lo + 4, str(lo), f"{lo} a {lo + 4} anos") for lo in range(5, 80, 5)),
    (80, 999, "80", "80 anos ou mais"),
)


def read_dbc(path: Path, fields: tuple[str, ...]) -> pl.DataFrame:
    """Lê os campos de um ``.dbc`` (DBF comprimido) como texto, um registro por linha."""
    import datasus_dbc  # noqa: PLC0415 - dependência só do DATASUS
    from dbfread import DBF  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        dbf_path = Path(tmp) / "dados.dbf"
        datasus_dbc.decompress(str(path), str(dbf_path))
        table = DBF(str(dbf_path), encoding="latin-1", char_decode_errors="replace")
        present = {f.name for f in table.fields}
        missing = [f for f in fields if f not in present]
        if missing:
            msg = f"{path.name}: campos ausentes {missing}"
            raise ParseError(msg)
        columns: dict[str, list[str | None]] = {f: [] for f in fields}
        for record in table:
            for f in fields:
                value = record.get(f)
                columns[f].append(None if value in (None, "") else str(value).strip())
    return pl.DataFrame(columns, schema=dict.fromkeys(fields, pl.String))


def _age_group() -> pl.Expr:
    code = pl.col("IDADE")
    unit = code.str.slice(0, 1)
    qty = code.str.slice(1, 2).cast(pl.Int32, strict=False)
    years = (
        pl.when(unit.is_in(["0", "1", "2", "3"]))
        .then(0)
        .when(unit == "4")
        .then(qty)
        .when(unit == "5")
        .then(qty + 100)
        .otherwise(None)
    )
    expr: Any = pl.when(years.is_null()).then(pl.lit(IGNORED[0] * 3))
    for lo, hi, cid, _ in AGE_GROUPS:
        expr = expr.when(years.is_between(lo, hi)).then(pl.lit(cid))
    result: pl.Expr = expr.otherwise(pl.lit(IGNORED[0] * 3))
    return result


def _chapter() -> pl.Expr:
    code = pl.col("CAUSABAS").str.to_uppercase().str.slice(0, 3)
    expr: Any = pl.when(code.is_null() | ~code.str.contains(r"^[A-Z]\d\d$")).then(pl.lit("99"))
    for first, last, roman, _ in CID10_CHAPTERS:
        expr = expr.when(code.is_between(pl.lit(first), pl.lit(last))).then(pl.lit(roman))
    result: pl.Expr = expr.otherwise(pl.lit("99"))
    return result


def _coded(column: str, labels: Mapping[str, str]) -> pl.Expr:
    col = pl.col(column).str.to_uppercase()
    return pl.when(col.is_in(list(labels))).then(col).otherwise(pl.lit(IGNORED[0]))


DIMENSIONS: tuple[tuple[str, str, Mapping[str, str]], ...] = (
    ("sexo", "Sexo", {"1": "Masculino", "2": "Feminino", IGNORED[0]: IGNORED[1]}),
    ("faixa", "Faixa etária", {cid: name for *_, cid, name in AGE_GROUPS} | {"999": "Ignorada"}),
    ("raca", "Cor ou raça", RACE | {IGNORED[0]: "Ignorada"}),
    (
        "capitulo",
        "Capítulo CID-10",
        {roman: f"{roman} {name}" for *_, roman, name in CID10_CHAPTERS} | {"99": "Sem causa"},
    ),
    ("local", "Local de ocorrência", PLACE | {IGNORED[0]: IGNORED[1]}),
)


TOTAL = "T"  # categoria Total de cada dimensão (o "0" já é "Menor de 1 ano")


def _marginals(frame: pl.DataFrame, level: str, keys: list[str]) -> pl.DataFrame:
    """Total e distribuição de cada dimensão (as demais no Total), por território.

    É o desenho das tabelas do SIDRA (Total + categorias): não cruza as
    dimensões, o que manteria quase um registro por óbito.
    """
    total_cols = {k: pl.lit(TOTAL) for k in keys}
    parts = [frame.group_by("territory_id").len().with_columns(**total_cols, dim=pl.lit("total"))]
    for key in keys:
        parts.append(
            frame.group_by("territory_id", key)
            .len()
            .with_columns(**{k: v for k, v in total_cols.items() if k != key}, dim=pl.lit(key))
        )
    columns = ["territory_id", *keys, "len", "dim"]
    return pl.concat([p.select(columns) for p in parts]).with_columns(
        pl.lit(level).alias("territorial_level")
    )


def sim_deaths(
    records: pl.DataFrame,
    *,
    uf: str,
    year: str,
    municipalities: Mapping[str, str],
    table_id: str,
    lineage: Lineage,
) -> pl.DataFrame:
    """Óbitos de um arquivo do SIM por município e na UF: Total e cada dimensão (observação).

    ``municipalities``: código de 6 dígitos → código IBGE de 7 dígitos (DTB).
    """
    if uf not in UF_CODES:
        msg = f"UF desconhecida no nome do arquivo: {uf}"
        raise ParseError(msg)
    coded = records.select(
        pl.col("CODMUNRES").str.slice(0, 6).alias("mun6"),
        pl.col("SEXO").str.to_uppercase().replace({"M": "1", "F": "2"}).alias("SEXO"),
        _age_group().alias("faixa"),
        _coded("RACACOR", RACE).alias("raca"),
        _chapter().alias("capitulo"),
        _coded("LOCOCOR", PLACE).alias("local"),
    ).with_columns(
        _coded("SEXO", {"1": "", "2": ""}).alias("sexo"),
        pl.col("mun6").replace_strict(municipalities, default=None).alias("mun7"),
    )
    keys = [d[0] for d in DIMENSIONS]
    located = coded.drop_nulls("mun7")
    frames = [
        _marginals(located.rename({"mun7": "territory_id"}), "6", keys),
        _marginals(coded.with_columns(pl.lit(UF_CODES[uf]).alias("territory_id")), "3", keys),
    ]
    frame = pl.concat(frames)
    expected = {"6": located.height, "3": records.height}
    for level, dim, total in (
        frame.group_by("territorial_level", "dim").agg(pl.col("len").sum()).iter_rows()
    ):
        if total != expected[level]:
            msg = f"agregação perdeu óbitos no nível {level} ({dim}): {total} de {expected[level]}"
            raise ParseError(msg)
    structs = [
        pl.struct(
            pl.lit(label).alias("dimension"),
            pl.col(key).alias("category_id"),
            pl.col(key)
            .replace_strict({TOTAL: "Total", **labels}, default="Ignorado")
            .alias("category_name"),
        )
        for key, label, labels in DIMENSIONS
    ]
    classification_key = pl.concat_str(
        [pl.lit(f"{label}=") + pl.col(key) for key, label, _ in DIMENSIONS], separator=";"
    )
    out = frame.select(
        pl.lit(table_id).alias("table_id"),
        pl.lit("obitos").alias("variable_id"),
        pl.lit("Óbitos por residência (SIM)").alias("variable_name"),
        pl.lit("obitos").alias("unit_id"),
        pl.lit("Óbitos").alias("unit_name"),
        pl.col("territorial_level"),
        pl.when(pl.col("territorial_level") == "6")
        .then(pl.lit("Município"))
        .otherwise(pl.lit("Unidade da Federação"))
        .alias("territorial_level_name"),
        pl.col("territory_id"),
        pl.lit(None, dtype=pl.String).alias("territory_name"),
        pl.lit(year).alias("period"),
        pl.lit(year).alias("period_name"),
        classification_key.alias("classification_key"),
        pl.concat_list(structs).alias("classifications"),
        pl.col("len").cast(pl.String).alias("value_raw"),
    ).with_columns(*classify_sidra_values(), *lineage.columns())
    return out.select(SIDRA_OBSERVATION.frame_schema().names()).cast(
        SIDRA_OBSERVATION.frame_schema()
    )
