"""Parsers Bronze → Silver.

Leitura eager (``json``/``read_excel``) justificada pelo volume: cada artefato
tem de 1 a 5 MB (no máximo cerca de 17 mil observações). As transformações
seguintes usam expressões Polars.
"""

from __future__ import annotations

import fnmatch
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import polars as pl
import shapefile  # pyshp
import shapely
from shapely.geometry import shape

from odb_processing.contracts import (
    CLASSIFICATION,
    DTB_MUNICIPALITY,
    SIDRA_OBSERVATION,
    TERRITORIAL_MESH,
)
from odb_processing.values import classify_sidra_values

# Grandes Regiões codificadas pelo 1º dígito do código da UF, convenção do IBGE
# confirmada pela API SIDRA (nível N2: Norte=1, Nordeste=2, Sudeste=3, Sul=4,
# Centro-Oeste=5; fixture t6579_n1n2n3_p2025.json).
REGIONS = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}


class ParseError(ValueError):
    """Artefato Bronze com estrutura inesperada."""


@dataclass(frozen=True, slots=True)
class Lineage:
    """Origem Bronze das observações e execução Silver que as produziu."""

    bronze_artifact_id: str
    bronze_checksum_sha256: str
    source_url: str
    retrieved_at: datetime
    ingestion_id: str
    silver_run_id: str
    processed_at: datetime

    def columns(self) -> list[pl.Expr]:
        """Colunas constantes de linhagem."""
        return [
            pl.lit(self.bronze_artifact_id).alias("bronze_artifact_id"),
            pl.lit(self.bronze_checksum_sha256).alias("bronze_checksum_sha256"),
            pl.lit(self.source_url).alias("source_url"),
            pl.lit(self.retrieved_at).cast(pl.Datetime("us", "UTC")).alias("retrieved_at"),
            pl.lit(self.ingestion_id).alias("ingestion_id"),
            pl.lit(self.silver_run_id).alias("silver_run_id"),
            pl.lit(self.processed_at).cast(pl.Datetime("us", "UTC")).alias("processed_at"),
        ]


# ------------------------------------------------------------------------- SIDRA


def parse_sidra(
    content: bytes,
    *,
    table_id: str,
    lineage: Lineage,
    territory_dim: str = "D1",
    variable_dim: str = "D2",
    period_dim: str = "D3",
) -> pl.DataFrame:
    """Resposta ``/values`` do SIDRA → observações no contrato ``sidra_observation``."""
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):  # noqa: PLR2004
        msg = "resposta SIDRA sem cabeçalho ou sem observações"
        raise ParseError(msg)
    header: dict[str, str] = payload[0]
    base = {territory_dim, variable_dim, period_dim}
    extra_dims = sorted(
        (k[:-1] for k in header if re.fullmatch(r"D\d+C", k) and k[:-1] not in base),
        key=lambda d: int(d[1:]),
    )
    raw = pl.DataFrame(payload[1:], schema=dict.fromkeys(header, pl.String), orient="row")

    classifications = (
        pl.concat_list(
            [
                pl.struct(
                    pl.lit(re.sub(r"\s*\(Código\)$", "", header[f"{d}C"])).alias("dimension"),
                    pl.col(f"{d}C").alias("category_id"),
                    pl.col(f"{d}N").alias("category_name"),
                )
                for d in extra_dims
            ]
        )
        if extra_dims
        else pl.lit([], dtype=pl.List(CLASSIFICATION))
    )
    classification_key = (
        pl.concat_str(
            [
                pl.lit(re.sub(r"\s*\(Código\)$", "", header[f"{d}C"]) + "=") + pl.col(f"{d}C")
                for d in extra_dims
            ],
            separator=";",
        )
        if extra_dims
        else pl.lit("")
    )
    frame = raw.select(
        pl.lit(table_id).alias("table_id"),
        pl.col(f"{variable_dim}C").alias("variable_id"),
        pl.col(f"{variable_dim}N").alias("variable_name"),
        pl.col("MC").alias("unit_id"),
        pl.col("MN").alias("unit_name"),
        pl.col("NC").alias("territorial_level"),
        pl.col("NN").alias("territorial_level_name"),
        pl.col(f"{territory_dim}C").alias("territory_id"),
        pl.col(f"{territory_dim}N").alias("territory_name"),
        pl.col(f"{period_dim}C").alias("period"),
        pl.col(f"{period_dim}N").alias("period_name"),
        classification_key.alias("classification_key"),
        classifications.alias("classifications"),
        pl.col("V").alias("value_raw"),
    ).with_columns(*classify_sidra_values(), *lineage.columns())
    return frame.select(SIDRA_OBSERVATION.frame_schema().names()).cast(
        SIDRA_OBSERVATION.frame_schema()
    )


# ------------------------------------------------------------------------- DTB

_DTB_COLUMNS = {
    "UF": "uf_id",
    "Nome_UF": "uf_name",
    "Região Geográfica Intermediária": "intermediate_region_id",
    "Nome Região Geográfica Intermediária": "intermediate_region_name",
    "Região Geográfica Imediata": "immediate_region_id",
    "Nome Região Geográfica Imediata": "immediate_region_name",
    "Município": "municipality_local_code",
    "Código Município Completo": "municipality_id",
    "Nome_Município": "municipality_name",
}
_DATA_BASE = re.compile(r"DATA BASE:\s*(\d{2})/(\d{2})/(\d{4})")


def extract_member(zip_path: Path, pattern: str) -> tuple[str, bytes]:
    """Lê do ZIP o único membro que corresponde ao padrão."""
    with zipfile.ZipFile(zip_path) as archive:
        matches = fnmatch.filter(archive.namelist(), pattern)
        if len(matches) != 1:
            msg = f"esperado 1 membro {pattern!r} no ZIP, encontrados {matches}"
            raise ParseError(msg)
        return matches[0], archive.read(matches[0])


def parse_dtb_municipalities(
    content: bytes, *, member: str, reference_year: str, lineage: Lineage
) -> pl.DataFrame:
    """Planilha ``RELATORIO_DTB_BRASIL_<ano>_MUNICIPIOS.ods`` → contrato ``dtb_municipality``.

    A planilha tem um bloco de títulos antes do cabeçalho. A linha de cabeçalho
    é localizada pelo conteúdo (primeira célula ``UF``), e não por posição fixa.
    A data base é lida do próprio arquivo (``DATA BASE: dd/mm/aaaa``).
    """
    sheet = pl.read_excel(
        io.BytesIO(content), engine="calamine", has_header=False, infer_schema_length=0
    )
    first = sheet.columns[0]
    header_rows = sheet.with_row_index().filter(pl.col(first) == "UF")["index"].to_list()
    if len(header_rows) != 1:
        msg = f"cabeçalho 'UF' não encontrado de forma única em {member}"
        raise ParseError(msg)
    header_at = header_rows[0]
    preamble = " ".join(
        str(v) for v in sheet.head(header_at).to_series(0).to_list() if v is not None
    )
    match = _DATA_BASE.search(preamble)
    if not match:
        msg = f"'DATA BASE' ausente no cabeçalho de {member}"
        raise ParseError(msg)
    day, month, year = (int(g) for g in match.groups())
    if str(year) != reference_year:
        msg = f"data base {year} difere do ano de referência {reference_year}"
        raise ParseError(msg)
    names = [str(v) for v in sheet.row(header_at)]
    missing = [c for c in _DTB_COLUMNS if c not in names]
    if missing:
        msg = f"colunas ausentes em {member}: {missing}"
        raise ParseError(msg)
    data = sheet.slice(header_at + 1)
    data.columns = names
    frame = (
        data.select([pl.col(src).str.strip_chars().alias(dst) for src, dst in _DTB_COLUMNS.items()])
        .filter(pl.col("municipality_id").is_not_null())
        .with_columns(
            pl.lit(reference_year).alias("reference_year"),
            pl.lit(date(year, month, day)).alias("reference_date"),
            pl.col("uf_id").str.slice(0, 1).alias("region_id"),
            pl.col("uf_id")
            .str.slice(0, 1)
            .replace_strict(REGIONS, default=None)
            .alias("region_name"),
            pl.lit(member).alias("source_member"),
            *lineage.columns(),
        )
    )
    return frame.select(DTB_MUNICIPALITY.frame_schema().names()).cast(
        DTB_MUNICIPALITY.frame_schema()
    )


# ------------------------------------------------------------------ malhas


# Datum das malhas do IBGE (o .prj não traz o código EPSG).
SIRGAS_2000 = "EPSG:4674"


@dataclass(frozen=True, slots=True)
class MeshSpec:
    """Como ler uma malha: membro do ZIP e campos do DBF."""

    dataset_id: str
    member: str
    level_id: str
    code_field: str
    name_field: str
    uf_field: str | None = None
    area_field: str = "AREA_KM2"


def parse_territorial_mesh(
    zip_path: Path, spec: MeshSpec, *, reference_year: str, lineage: Lineage
) -> pl.DataFrame:
    """Shapefile de malha do IBGE (ZIP) → contrato ``territorial_mesh``.

    A geometria é preservada sem simplificação, em WKB. O datum é conferido no
    ``.prj`` (SIRGAS 2000, coordenadas geográficas). A leitura é eager: o
    shapefile não tem leitura em fluxo útil aqui e cabe em memória (a malha
    municipal tem cerca de 17 milhões de vértices).
    """
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        needed = [f"{spec.member}.{ext}" for ext in ("shp", "shx", "dbf", "prj")]
        missing = [n for n in needed if n not in names]
        if missing:
            msg = f"membros ausentes no ZIP: {missing}"
            raise ParseError(msg)
        prj = archive.read(f"{spec.member}.prj").decode("ascii", errors="replace")
        if "SIRGAS_2000" not in prj or not prj.startswith("GEOGCS"):
            msg = f"{spec.member}.prj: sistema de referência inesperado: {prj[:80]!r}"
            raise ParseError(msg)
        cpg = f"{spec.member}.cpg"
        encoding = archive.read(cpg).decode().strip() if cpg in names else "utf-8"
        reader = shapefile.Reader(
            shp=io.BytesIO(archive.read(f"{spec.member}.shp")),
            shx=io.BytesIO(archive.read(f"{spec.member}.shx")),
            dbf=io.BytesIO(archive.read(f"{spec.member}.dbf")),
            encoding=encoding,
        )
        fields = [f[0] for f in reader.fields[1:]]
        wanted = [spec.code_field, spec.name_field, spec.area_field]
        if spec.uf_field:
            wanted.append(spec.uf_field)
        absent = [f for f in wanted if f not in fields]
        if absent:
            msg = f"{spec.member}.dbf: campos ausentes {absent} (há {fields})"
            raise ParseError(msg)
        codes: list[str] = []
        names_: list[str] = []
        ufs: list[str | None] = []
        areas: list[float | None] = []
        wkbs: list[bytes] = []
        for record in reader.iterShapeRecords():
            attrs = record.record.as_dict()
            geometry = shape(record.shape.__geo_interface__)
            codes.append(str(attrs[spec.code_field]).strip())
            names_.append(str(attrs[spec.name_field]).strip())
            ufs.append(str(attrs[spec.uf_field]).strip() if spec.uf_field else None)
            area = attrs[spec.area_field]
            areas.append(None if area is None else float(area))
            wkbs.append(shapely.to_wkb(geometry))
    geoms = shapely.from_wkb(wkbs)
    frame = pl.DataFrame(
        {
            "code": codes,
            "name": names_,
            "uf_abbreviation": ufs,
            "area_km2": areas,
            "geometry_wkb": wkbs,
            "vertex_count": shapely.get_num_coordinates(geoms).tolist(),
        },
        schema_overrides={
            "uf_abbreviation": pl.String(),
            "area_km2": pl.Float64(),
            "geometry_wkb": pl.Binary(),
            "vertex_count": pl.Int64(),
        },
    )
    return frame.with_columns(
        pl.lit(spec.dataset_id).alias("dataset_id"),
        pl.lit(reference_year).alias("reference_year"),
        pl.lit(spec.level_id).alias("level_id"),
        pl.lit(SIRGAS_2000).alias("crs"),
        pl.lit(f"{spec.member}.shp").alias("source_member"),
        *lineage.columns(),
    ).select(list(TERRITORIAL_MESH.schema))
