"""Agregação dos óbitos do SIM por município (Silver), com registros sintéticos."""

from __future__ import annotations

import struct
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from odb_processing.datasus import SIM_FIELDS, dbf_record_count, other_uf_residents, sim_deaths
from odb_processing.parsers import Lineage, ParseError
from odb_processing.quality import CheckStatus, sim_checks

LINEAGE = Lineage(
    "a", "b" * 64, "ftp://x/DOAC2023.dbc", datetime.now(UTC), "i", "r", datetime.now(UTC)
)
MUNICIPALITIES = {"120040": "1200401", "120020": "1200203"}


def _records(rows: list[tuple[str | None, ...]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=dict.fromkeys(SIM_FIELDS, pl.String), orient="row")


RECORDS = _records(
    [
        # DTOBITO, CODMUNRES, SEXO, IDADE, RACACOR, CAUSABAS, LOCOCOR
        ("01012023", "120040", "1", "475", "4", "I219", "1"),  # 75 anos, circulatório
        ("02012023", "120040", "2", "210", "1", "P073", "1"),  # 10 dias: menor de 1 ano
        ("03012023", "120020", "M", "530", "", "C509", "3"),  # 130 anos: 80+; sexo antigo "M"
        ("04012023", "120000", "9", None, "9", None, "9"),  # município e campos ignorados
        ("05012023", "120040", "1", "432", "5", "X959", "4"),  # 32 anos, causas externas
    ]
)


def _deaths() -> pl.DataFrame:
    return sim_deaths(
        RECORDS,
        uf="AC",
        year="2023",
        municipalities=MUNICIPALITIES,
        table_id="SIM-DORES",
        lineage=LINEAGE,
    )


def _value(frame: pl.DataFrame, level: str, territory: str, **dims: str) -> float:
    key = {"Sexo": "T", "Faixa etária": "T", "Cor ou raça": "T", "Capítulo CID-10": "T"}
    key |= {"Local de ocorrência": "T"} | dims
    wanted = ";".join(f"{k}={v}" for k, v in key.items())
    row = frame.filter(
        (pl.col("territorial_level") == level)
        & (pl.col("territory_id") == territory)
        & (pl.col("classification_key") == wanted)
    )
    return float(row["value"].sum())


def test_totals_by_municipality_and_state() -> None:
    out = _deaths()
    assert _value(out, "3", "12") == 5  # UF: todos, inclusive o de município ignorado
    assert _value(out, "6", "1200401") == 3
    assert _value(out, "6", "1200203") == 1
    assert "1200000" not in out["territory_id"].to_list()


def test_dimension_decoding() -> None:
    out = _deaths()
    assert _value(out, "3", "12", **{"Faixa etária": "0"}) == 1  # menor de 1 ano
    assert _value(out, "3", "12", **{"Faixa etária": "80"}) == 1  # 130 anos
    assert _value(out, "3", "12", **{"Faixa etária": "999"}) == 1  # idade ignorada
    assert _value(out, "3", "12", Sexo="1") == 3  # "1" e "M"
    assert _value(out, "3", "12", **{"Capítulo CID-10": "IX"}) == 1
    assert _value(out, "3", "12", **{"Capítulo CID-10": "XVI"}) == 1  # perinatal (P07)
    assert _value(out, "3", "12", **{"Capítulo CID-10": "XX"}) == 1  # X95
    assert _value(out, "3", "12", **{"Capítulo CID-10": "99"}) == 1  # sem causa
    assert _value(out, "3", "12", **{"Cor ou raça": "9"}) == 2  # vazio e 9
    names = out.explode("classifications", empty_as_null=True).unnest("classifications")
    chapter = names.filter(pl.col("category_id") == "IX")["category_name"][0]
    assert chapter.startswith("IX Doenças do aparelho circulatório")


def test_each_dimension_sums_to_the_total() -> None:
    out = _deaths().filter(pl.col("territorial_level") == "3")
    exploded = out.explode("classifications", empty_as_null=True).unnest("classifications")
    for dim in ("Sexo", "Faixa etária", "Cor ou raça", "Capítulo CID-10", "Local de ocorrência"):
        parts = exploded.filter((pl.col("dimension") == dim) & (pl.col("category_id") != "T"))[
            "value"
        ].sum()
        assert float(parts) == 5, dim
    assert out["value_status"].unique().to_list() == ["valid"]


def test_unknown_state_is_rejected() -> None:
    with pytest.raises(ParseError, match="UF desconhecida"):
        sim_deaths(
            RECORDS,
            uf="XX",
            year="2023",
            municipalities=MUNICIPALITIES,
            table_id="SIM-DORES",
            lineage=LINEAGE,
        )


def _dbf(path: Path, flags: bytes) -> Path:
    """DBF mínimo (um campo C de 3 bytes); ``flags`` traz o 1º byte de cada registro."""
    field = b"CAMPO".ljust(11, b"\0") + b"C" + b"\0" * 4 + bytes([3]) + b"\0" * 15
    headerlen, recordlen = 32 + len(field) + 1, 1 + 3
    header = struct.pack("<B3BIHH", 3, 126, 1, 1, len(flags), headerlen, recordlen).ljust(32, b"\0")
    records = b"".join(bytes([f]) + b"abc" for f in flags)
    path.write_bytes(header + field + b"\r" + records + b"\x1a")
    return path


def test_dbf_record_count_skips_deleted_records(tmp_path: Path) -> None:
    assert dbf_record_count(_dbf(tmp_path / "a.dbf", b"  *  ")) == 4


def test_dbf_record_count_rejects_truncated_file(tmp_path: Path) -> None:
    path = _dbf(tmp_path / "a.dbf", b"   ")
    path.write_bytes(path.read_bytes()[:-5])
    with pytest.raises(ParseError, match="inconsistente"):
        dbf_record_count(path)


def test_sim_checks() -> None:
    same, none = sim_checks({"2023": {"states": 10, "national": 10}}, {})
    assert (same.status, none.status) == (CheckStatus.PASS, CheckStatus.PASS)
    differ, moved = sim_checks(
        {"2023": {"states": 10, "national": 11}, "2024": {"states": 5, "national": None}},
        {"DOGO1999.dbc": {"17": 10}},
    )
    assert differ.status is CheckStatus.WARN
    assert differ.details == {
        "differ": {"2023": {"states": 10, "national": 11}},
        "missing": ["2024"],
    }
    assert (moved.status, moved.observed) == (CheckStatus.WARN, 10)


def test_resident_of_another_state_counts_only_in_the_file_state() -> None:
    # Arquivo do Acre com um residente do Amazonas (130260 → Manaus).
    records = pl.concat([RECORDS, _records([("06012023", "130260", "1", "450", "1", "I10", "1")])])
    assert other_uf_residents(records, "AC") == {"13": 1}
    frame = sim_deaths(
        records,
        uf="AC",
        year="2023",
        municipalities=MUNICIPALITIES | {"130260": "1302603"},
        table_id="SIM-DORES",
        lineage=LINEAGE,
    )
    assert _value(frame, "3", "12") == 6
    assert frame.filter(pl.col("territory_id") == "1302603").is_empty()
