"""Exportações de KPIs (§19.3): CSV, XLSX, Parquet e JSON.

Toda exportação leva os metadados: KPI, indicador, unidade, fonte oficial,
licença, filtros, release e versões das tabelas, data de geração e avisos.

* CSV: ZIP com ``dados.csv`` (UTF-8 com BOM, para abrir no Excel) e ``metadados.json``;
* XLSX: planilhas ``dados`` e ``metadados``;
* Parquet: metadados no rodapé do arquivo (chave ``odb_metadata``);
* JSON: ``{"metadata": ..., "rows": [...]}``.

Valores ausentes ficam vazios, nunca zero, e a coluna ``status`` diz o motivo
(por exemplo ``suppressed`` para o ``X`` do IBGE).
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import polars as pl

from odb_api.kpis import Observation
from odb_api.schemas import ExportFormat, Provenance

MEDIA_TYPES: dict[str, str] = {
    "csv": "application/zip",
    "parquet": "application/vnd.apache.parquet",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
}
EXTENSIONS = {"csv": "zip", "parquet": "parquet", "xlsx": "xlsx", "json": "json"}


class ExportTooLargeError(ValueError):
    """Resultado acima do limite de linhas da exportação."""


def frame(
    observations: Sequence[Observation],
    *,
    dims: Sequence[str],
    labels: Mapping[str, str],
    category_names: Mapping[str, str],
    ufs: Mapping[str, str | None],
    unit: str,
) -> pl.DataFrame:
    """Formato longo: território, período, uma coluna por dimensão, valor e estado."""
    data: dict[str, list[Any]] = {
        "geography_key": [o.geography_key for o in observations],
        "territorio": [o.name for o in observations],
        "uf": [ufs.get(o.geography_key) for o in observations],
        "periodo": [o.period for o in observations],
    }
    for i, dim in enumerate(dims):
        data[labels.get(dim, dim)] = [category_names[o.combo[i]] for o in observations]
    values = [o.value for o in observations]
    # Contagens saem como inteiros; razões e áreas mantêm as casas publicadas.
    integral = all(v is None or v == v.to_integral_value() for v in values)
    data["valor"] = [None if v is None else (int(v) if integral else float(v)) for v in values]
    data["status"] = [o.status for o in observations]
    data["unidade"] = [unit] * len(observations)
    return pl.DataFrame(
        data, schema_overrides={"valor": pl.Int64 if integral else pl.Float64, "uf": pl.String}
    )


def metadata(
    *,
    kpi: Mapping[str, Any],
    indicator: Mapping[str, Any],
    dataset: Mapping[str, Any] | None,
    filters: Mapping[str, Any],
    provenance: Provenance,
    rows: int,
) -> dict[str, Any]:
    """Metadados que acompanham a exportação."""
    return {
        "aviso": (
            "Cópia exportada da Plataforma de Dados Abertos (não oficial). A fonte oficial "
            "é o IBGE; os valores vêm do release Gold indicado, sem alteração."
        ),
        "gerado_em": datetime.now(UTC).isoformat(),
        "kpi": dict(kpi),
        "indicador": {
            k: indicator.get(k)
            for k in (
                "indicator_id",
                "name",
                "description",
                "unit",
                "additivity",
                "source_table_id",
                "source_variable_id",
                "source_variable_name",
                "reference_url",
                "caveats",
            )
        },
        "fonte": dict(dataset) if dataset else None,
        "filtros": dict(filters),
        "release": provenance.model_dump(),
        "linhas": rows,
        "legenda_status": {
            "valid": "valor publicado",
            "true_zero": "zero publicado",
            "rounded_zero": "zero por arredondamento",
            "suppressed": "suprimido pela fonte (X): ausente, não é zero",
            "not_available": "não disponível (...)",
            "not_applicable": "não se aplica (..)",
            "absent": "combinação não publicada",
        },
    }


def render(data: pl.DataFrame, meta: Mapping[str, Any], fmt: ExportFormat) -> bytes:
    """Arquivo final no formato pedido."""
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2, default=str)
    if fmt == "json":
        return json.dumps(
            {"metadata": meta, "rows": data.to_dicts()}, ensure_ascii=False, default=str
        ).encode()
    if fmt == "parquet":
        buffer = io.BytesIO()
        data.write_parquet(buffer, metadata={"odb_metadata": meta_json})
        return buffer.getvalue()
    if fmt == "xlsx":
        buffer = io.BytesIO()
        flat = [
            {"campo": k, "valor": v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}
            for k, v in meta.items()
        ]
        import xlsxwriter  # noqa: PLC0415 - só a exportação XLSX precisa

        with xlsxwriter.Workbook(buffer) as workbook:
            data.write_excel(workbook, worksheet="dados")
            pl.DataFrame(flat).write_excel(workbook, worksheet="metadados")
        return buffer.getvalue()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("dados.csv", "﻿" + data.write_csv())
        archive.writestr("metadados.json", meta_json)
    return buffer.getvalue()
