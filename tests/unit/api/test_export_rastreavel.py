"""Precisão, segurança e rastreabilidade comuns aos quatro formatos exportados."""

from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from odb_api.dictionaries import DictionaryCatalog
from odb_api.exports import frame, merge_provenance, metadata, render
from odb_api.kpis import Observation
from odb_api.schemas import ExportFormat, Provenance, TableVersionOut
from odb_semantics import SemanticError

ROOT = Path(__file__).resolve().parents[3]


def _example() -> tuple[pl.DataFrame, dict[str, Any]]:
    observations = [
        Observation(
            "uf:25", "=1+2", "2024", ("c240:0015",), Decimal("1234567890123456.789012"), "valid"
        ),
        Observation("uf:25", "Paraíba", "2024", ("c240:0016",), None, "suppressed"),
        Observation("uf:25", "Paraíba", "2024", ("c240:0017",), Decimal(0), "true_zero"),
    ]
    data = frame(
        observations,
        dims=["c240"],
        labels={"c240": "Idade"},
        category_names={f"c240:00{i}": str(i) for i in (15, 16, 17)},
        ufs={},
        unit="Pessoas",
    )
    meta = metadata(
        kpi={"kpi_id": "nascidos_vivos", "label": "Nascidos vivos"},
        indicator={},
        dataset={"source_id": "teste", "license_id": "licenca-teste"},
        filters={"categories": ["c240:0015"]},
        provenance=Provenance(release_id="teste", tables=[]),
        rows=data.height,
        documentation=DictionaryCatalog(ROOT / "docs/data_catalog/dicionarios-2026-11-26").entry(
            "nascidos_vivos"
        ),
        columns=data.schema,
    )
    return data, meta


@pytest.mark.parametrize("fmt", ["csv", "json", "parquet", "xlsx"])
def test_decimal_codigo_sigilo_zero_e_metadados_sobrevivem_aos_formatos(fmt: ExportFormat) -> None:
    data, meta = _example()
    content = render(data, meta, fmt)
    if fmt == "json":
        obj = json.loads(content)
        result = pl.DataFrame(obj["rows"])
        exported = obj["metadata"]
    elif fmt == "csv":
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            result = pl.read_csv(io.BytesIO(archive.read("dados.csv")), infer_schema=False)
            exported = json.loads(archive.read("metadados.json"))
    elif fmt == "parquet":
        result = pl.read_parquet(io.BytesIO(content))
        exported = json.loads(pl.read_parquet_metadata(io.BytesIO(content))["odb_metadata"])
    else:
        result = pl.read_excel(io.BytesIO(content), sheet_name="dados", infer_schema_length=None)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            book = ET.fromstring(archive.read("xl/workbook.xml"))  # noqa: S314 - XML gerado no teste
            assert [s.attrib["name"] for s in book.findall("m:sheets/m:sheet", ns)] == [
                "Apresentação",
                "dados",
                "metadados",
                "dicionario",
                "fontes",
                "metodos",
            ]
            assert len([n for n in archive.namelist() if n.startswith("xl/tables/table")]) == 5
            assert not any(
                ET.fromstring(archive.read(n)).findall(".//m:f", ns)  # noqa: S314 - XML do teste
                for n in archive.namelist()
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
            )
        exported = meta
    assert str(result["value_exact"][0]) == "1234567890123456.789012"
    assert result["value_exact"][1] is None
    assert str(result["value_exact"][2]) == "0"
    assert str(result["c240_code"][0]) == "0015"
    assert result["status"].to_list() == ["valid", "suppressed", "true_zero"]
    assert exported["artifact"]["generator_name"] == "Open Data Brasil"
    assert exported["filtros"]["categories"] == ["c240:0015"]
    assert exported["documentacao"]["document"]["lacunas"]


def test_uniao_de_proveniencia_preserva_todas_as_tabelas_e_bloqueia_conflitos() -> None:
    a = Provenance(release_id="r", tables=[TableVersionOut(table_id="a", delta_version=1)])
    b = Provenance(
        release_id="r", tables=[TableVersionOut(table_id="b", delta_version=2)], derived=True
    )
    merged = merge_provenance([a, b], "r")
    assert {t.table_id for t in merged.tables} == {"a", "b"}
    assert merged.derived
    with pytest.raises(SemanticError, match="releases diferentes"):
        merge_provenance([a, b.model_copy(update={"release_id": "outro"})], "r")
    with pytest.raises(SemanticError, match="versões divergentes"):
        merge_provenance(
            [a, a.model_copy(update={"tables": [TableVersionOut(table_id="a", delta_version=2)]})],
            "r",
        )


def test_metadado_extenso_tem_partes_recomponiveis_sem_truncamento() -> None:
    data, meta = _example()
    meta["texto_extenso"] = "ação" * 20_000
    content = render(data, meta, "xlsx")
    rows = pl.read_excel(io.BytesIO(content), sheet_name="metadados").filter(
        pl.col("campo") == "texto_extenso"
    )
    assert rows.height > 1
    assert "".join(rows.sort("parte")["valor"].to_list()) == meta["texto_extenso"]


def test_catalogo_inclui_todas_as_fichas_apoios_e_candidatas_sem_promocao() -> None:
    catalog = DictionaryCatalog(ROOT / "docs/data_catalog/dicionarios-2026-11-26")
    assert len(catalog.documents) == 335
    assert sum(d["kpi_id"] is None for d in catalog.documents.values()) == 44
    assert len(catalog.expansions) == 50
    for key in catalog.documents:
        entry = catalog.entry(key)
        assert entry.document["lacunas"]
        assert entry.documentary_status == "revisao_parcial"
