import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from odb_processing.contracts import DTB_MUNICIPALITY, SIDRA_OBSERVATION, TERRITORIAL_MESH
from odb_processing.parsers import (
    REGIONS,
    Lineage,
    MeshSpec,
    ParseError,
    extract_member,
    parse_dtb_municipalities,
    parse_sidra,
    parse_territorial_mesh,
)
from odb_processing.quality import CheckStatus, mesh_checks
from tests.ingestion_support import (
    DTB_FIXTURES,
    MESH_MUNICIPALITIES,
    SIDRA_FIXTURES,
    make_mesh_zip,
)

LINEAGE = Lineage(
    bronze_artifact_id="artifact-1",
    bronze_checksum_sha256="a" * 64,
    source_url="https://apisidra.ibge.gov.br/values/...",
    retrieved_at=datetime(2026, 11, 3, 18, 0, tzinfo=UTC),
    ingestion_id="ingestion-1",
    silver_run_id="run-1",
    processed_at=datetime(2026, 11, 3, 19, 0, tzinfo=UTC),
)
DTB_ODS = DTB_FIXTURES / "RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.ods"


def _sidra(name: str) -> bytes:
    return (SIDRA_FIXTURES / name).read_bytes()


def test_parse_real_sidra_census() -> None:
    frame = parse_sidra(_sidra("t4714_n1n2n3_p2022.json"), table_id="4714", lineage=LINEAGE)
    assert frame.schema == SIDRA_OBSERVATION.frame_schema()
    assert frame.height == 99
    assert not frame.select(SIDRA_OBSERVATION.key).is_duplicated().any()
    brasil = frame.filter((pl.col("territorial_level") == "1") & (pl.col("variable_id") == "93"))
    assert brasil.select("territory_name", "value", "unit_name", "period").row(0) == (
        "Brasil",
        Decimal("203080756"),
        "Pessoas",
        "2022",
    )
    area = frame.filter((pl.col("territorial_level") == "1") & (pl.col("variable_id") == "6318"))
    assert area.select("value_raw", "value_decimals").row(0) == ("8510417.771", 3)
    assert frame["bronze_artifact_id"].unique().to_list() == ["artifact-1"]
    assert frame["classification_key"].unique().to_list() == [""]
    assert frame["retrieved_at"].dtype == pl.Datetime("us", "UTC")


def test_regions_convention_matches_sidra_n2() -> None:
    """A regra 1º dígito da UF → Grande Região confere com o nível N2 publicado."""
    frame = parse_sidra(_sidra("t6579_n1n2n3_p2025.json"), table_id="6579", lineage=LINEAGE)
    n2 = dict(
        frame.filter(pl.col("territorial_level") == "2")
        .select("territory_id", "territory_name")
        .iter_rows()
    )
    assert n2 == REGIONS


def test_parse_sidra_with_classification_dimensions() -> None:
    payload = json.loads(_sidra("t6579_n1n2n3_p2025.json"))
    payload[0].update({"D4C": "Sexo (Código)", "D4N": "Sexo"})
    for i, row in enumerate(payload[1:]):
        row.update({"D4C": "4" if i % 2 else "5", "D4N": "Homens" if i % 2 else "Mulheres"})
    frame = parse_sidra(json.dumps(payload).encode(), table_id="6579", lineage=LINEAGE)
    first = frame.row(0, named=True)
    assert first["classification_key"] == "Sexo=5"
    assert first["classifications"] == [
        {"dimension": "Sexo", "category_id": "5", "category_name": "Mulheres"}
    ]


@pytest.mark.parametrize("content", [b"[]", b'[{"NC": "x"}]', b'{"a": 1}'])
def test_parse_sidra_rejects_empty(content: bytes) -> None:
    with pytest.raises(ParseError):
        parse_sidra(content, table_id="1", lineage=LINEAGE)


def test_parse_real_dtb_2025() -> None:
    frame = parse_dtb_municipalities(
        DTB_ODS.read_bytes(), member=DTB_ODS.name, reference_year="2025", lineage=LINEAGE
    )
    assert frame.schema == DTB_MUNICIPALITY.frame_schema()
    assert frame.height == 5571
    assert frame["reference_date"].unique().to_list() == [date(2025, 12, 31)]
    assert frame["uf_id"].n_unique() == 27
    assert not frame["municipality_id"].is_duplicated().any()
    regions = dict(frame.group_by("region_name").len().iter_rows())
    assert sum(regions.values()) == 5571
    row = frame.filter(pl.col("municipality_id") == "5101837").row(0, named=True)
    assert (row["municipality_name"], row["uf_name"], row["region_name"]) == (
        "Boa Esperança do Norte",
        "Mato Grosso",
        "Centro-Oeste",
    )
    alta = frame.filter(pl.col("municipality_id") == "1100015").row(0, named=True)
    assert alta["municipality_name"] == "Alta Floresta D'Oeste"
    assert alta["municipality_local_code"] == "00015"


def test_dtb_reference_year_must_match() -> None:
    with pytest.raises(ParseError, match="difere do ano"):
        parse_dtb_municipalities(
            DTB_ODS.read_bytes(), member="x", reference_year="2024", lineage=LINEAGE
        )


def test_extract_member(tmp_path: Path) -> None:
    archive = tmp_path / "a.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.ods", b"x")
        z.writestr("RELATORIO_DTB_BRASIL_2025_DISTRITOS.ods", b"y")
    name, content = extract_member(archive, "RELATORIO_DTB_BRASIL_*_MUNICIPIOS.ods")
    assert (name, content) == ("RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.ods", b"x")
    with pytest.raises(ParseError, match="encontrados"):
        extract_member(archive, "RELATORIO_*")
    with pytest.raises(ParseError, match="encontrados"):
        extract_member(archive, "nada*")


def _sheet(rows: list[list[str | None]]) -> pl.DataFrame:
    width = max(len(r) for r in rows)
    padded = [r + [None] * (width - len(r)) for r in rows]
    return pl.DataFrame(padded, schema=[f"c{i}" for i in range(width)], orient="row")


HEADER = [
    "UF",
    "Nome_UF",
    "Região Geográfica Intermediária",
    "Nome Região Geográfica Intermediária",
    "Região Geográfica Imediata",
    "Nome Região Geográfica Imediata",
    "Município",
    "Código Município Completo",
    "Nome_Município",
]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([["DATA BASE: 31/12/2025"], ["x"]], "cabeçalho 'UF'"),
        ([["TÍTULO"], HEADER], "DATA BASE"),
        ([["DATA BASE: 31/12/2025"], ["UF", "Nome_UF"]], "colunas ausentes"),
    ],
)
def test_dtb_structure_errors(
    monkeypatch: pytest.MonkeyPatch, rows: list[list[str | None]], message: str
) -> None:
    monkeypatch.setattr(pl, "read_excel", lambda *_a, **_k: _sheet(rows))
    with pytest.raises(ParseError, match=message):
        parse_dtb_municipalities(b"", member="m.ods", reference_year="2025", lineage=LINEAGE)


MUNI_SPEC = MeshSpec(
    dataset_id="ibge-malha-municipios-2022",
    member="BR_Municipios_2022",
    level_id="municipio",
    code_field="CD_MUN",
    name_field="NM_MUN",
    uf_field="SIGLA_UF",
)


def _mesh(tmp_path: Path, content: bytes) -> Path:
    path = tmp_path / "malha.zip"
    path.write_bytes(content)
    return path


def test_parse_territorial_mesh_and_checks(tmp_path: Path) -> None:
    content = make_mesh_zip(
        "BR_Municipios_2022", ["CD_MUN", "NM_MUN", "SIGLA_UF"], MESH_MUNICIPALITIES
    )
    frame = parse_territorial_mesh(
        _mesh(tmp_path, content), MUNI_SPEC, reference_year="2022", lineage=LINEAGE
    )
    assert frame.schema == TERRITORIAL_MESH.frame_schema()
    assert frame["code"].to_list()[:2] == ["1100015", "2927408"]
    assert set(frame["crs"].to_list()) == {"EPSG:4674"}
    assert frame["vertex_count"].to_list() == [5] * 5
    checks = {
        c.check_id: c
        for c in mesh_checks(
            frame,
            TERRITORIAL_MESH,
            expected_count=5,
            reference_ids={"1100015", "2927408", "5103403", "5101837"},
            reference_label="DTB",
        )
    }
    assert checks["geometry.valid"].status is CheckStatus.PASS
    assert checks["coverage.count"].status is CheckStatus.PASS
    reference = checks["reference.territory"]
    assert reference.status is CheckStatus.WARN
    assert [d["name"] for d in reference.details["not_in_reference"]] == [
        "Lagoa Mirim",
        "Lagoa dos Patos",
    ]
    assert reference.details["without_geometry"] == ["5101837"]


def test_mesh_rejects_wrong_crs_members_and_fields(tmp_path: Path) -> None:
    good = make_mesh_zip("BR_Municipios_2022", ["CD_MUN", "NM_MUN", "SIGLA_UF"], [("1", "a", "b")])
    with zipfile.ZipFile(_mesh(tmp_path, good)) as src:
        files = {n: src.read(n) for n in src.namelist()}

    def rebuild(**changes: bytes | None) -> Path:
        out = tmp_path / "alterada.zip"
        with zipfile.ZipFile(out, "w") as dst:
            for name, data in {**files, **changes}.items():
                if data is not None:
                    dst.writestr(name, data)
        return out

    with pytest.raises(ParseError, match="sistema de referência"):
        parse_territorial_mesh(
            rebuild(**{"BR_Municipios_2022.prj": b'PROJCS["SIRGAS_2000_UTM"]'}),
            MUNI_SPEC,
            reference_year="2022",
            lineage=LINEAGE,
        )
    with pytest.raises(ParseError, match="membros ausentes"):
        parse_territorial_mesh(
            rebuild(**{"BR_Municipios_2022.dbf": None}),
            MUNI_SPEC,
            reference_year="2022",
            lineage=LINEAGE,
        )
    other = make_mesh_zip("BR_Municipios_2022", ["CD_X", "NM_MUN", "SIGLA_UF"], [("1", "a", "b")])
    with pytest.raises(ParseError, match="campos ausentes"):
        parse_territorial_mesh(
            _mesh(tmp_path, other), MUNI_SPEC, reference_year="2022", lineage=LINEAGE
        )
