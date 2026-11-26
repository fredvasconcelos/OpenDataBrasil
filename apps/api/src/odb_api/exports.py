"""Exportações de KPIs (§19.3): CSV, XLSX, Parquet e JSON.

Toda exportação leva os metadados: KPI, indicador, unidade, fonte oficial,
licença, filtros, release e versões das tabelas, data de geração e avisos.

* CSV: ZIP com ``dados.csv`` (UTF-8 com BOM, para abrir no Excel) e ``metadados.json``;
* XLSX: apresentação, dados, metadados, dicionário, fontes e métodos;
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
from decimal import Decimal
from typing import Any

import polars as pl

from odb_api.dictionaries import DictionaryEntryOut
from odb_api.export_workbook import WorkbookLimitError, render_workbook
from odb_api.kpis import Observation
from odb_api.schemas import ExportFormat, Provenance, TableVersionOut
from odb_semantics import SemanticError

MEDIA_TYPES: dict[str, str] = {
    "csv": "application/zip",
    "parquet": "application/vnd.apache.parquet",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
}
EXTENSIONS = {"csv": "zip", "parquet": "parquet", "xlsx": "xlsx", "json": "json"}


class ExportTooLargeError(ValueError):
    """Resultado acima do limite de linhas da exportação."""


def row_limit(kpi_id: str, default: int) -> int:
    """Aplica os 200 mil autorizados em 18/11/2026 apenas aos dois KPIs LSPA.

    A auditoria D0 encontrou 162.675 e 137.592 linhas por UF/produto. As seis
    medidas municipais do PIB e os demais KPIs conservam o limite padrão.
    """
    return 200_000 if kpi_id in {"safra_estimada", "safra_area_colhida"} else default


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
    # Publicados vêm em Decimal; derivados por média (ADR-0017) podem vir em float.
    integral = all(
        v is None
        or (v == v.to_integral_value() if isinstance(v, Decimal) else float(v).is_integer())
        for v in values
    )
    integral = integral and all(v is None or -(2**63) <= v < 2**63 for v in values)
    data["valor"] = [None if v is None else (int(v) if integral else float(v)) for v in values]
    data["status"] = [o.status for o in observations]
    data["unidade"] = [unit] * len(observations)
    # O número auxiliar pode perder precisão; esta coluna conserva o Decimal recebido.
    data["value_exact"] = [
        None if v is None else format(v if isinstance(v, Decimal) else Decimal(str(v)), "f")
        for v in values
    ]
    data["source_table_id"] = [o.source for o in observations]
    for i, dim in enumerate(dims):
        data[f"{dim}_code"] = [o.combo[i].split(":", 1)[1] for o in observations]
        data[f"{dim}_category_key"] = [o.combo[i] for o in observations]
    return pl.DataFrame(
        data, schema_overrides={"valor": pl.Int64 if integral else pl.Float64, "uf": pl.String}
    )


def tag(data: pl.DataFrame, *, level: str, grain: str, kind: str) -> pl.DataFrame:
    """Colunas da exportação ampliada (B5): nível, grão e tipo (publicado ou derivado)."""
    return data.with_columns(
        pl.lit(level).alias("nivel"), pl.lit(grain).alias("grao"), pl.lit(kind).alias("tipo")
    ).select(["nivel", "grao", *data.columns[:4], *data.columns[4:], "tipo"])


def concat(frames: Sequence[pl.DataFrame]) -> pl.DataFrame:
    """Junta as partes; contagens inteiras e médias decimais viram decimal juntas."""
    if len(frames) == 1:
        return frames[0]
    return pl.concat(list(frames), how="diagonal_relaxed")


def merge_provenance(items: Sequence[Provenance], release_id: str) -> Provenance:
    """Une tabelas de todas as partes; recusa releases ou versões contraditórios."""
    versions: dict[str, TableVersionOut] = {}
    for item in items:
        if item.release_id != release_id:
            raise SemanticError("a exportação recebeu partes de releases diferentes")
        for table in item.tables:
            previous = versions.get(table.table_id)
            if previous and previous.delta_version != table.delta_version:
                raise SemanticError("a exportação recebeu versões divergentes da mesma tabela")
            versions[table.table_id] = table
    return items[0].model_copy(
        update={
            "tables": list(versions.values()),
            "derived": any(p.derived for p in items),
            "truncated": any(p.truncated for p in items),
            **{
                field: getattr(items[0], field)
                if len({getattr(item, field) for item in items}) == 1
                else None
                for field in ("correction", "correction_label", "price_base")
            },
        }
    )


def metadata(
    *,
    kpi: Mapping[str, Any],
    indicator: Mapping[str, Any],
    dataset: Mapping[str, Any] | None,
    filters: Mapping[str, Any],
    provenance: Provenance,
    rows: int,
    documentation: DictionaryEntryOut | None = None,
    blocks: Sequence[Mapping[str, Any]] = (),
    columns: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Metadados que acompanham a exportação."""
    generated = datetime.now(UTC).isoformat()
    document = documentation.model_dump() if documentation else None
    dictionary = [
        {
            "campo": key,
            "tipo": str(value),
            "definicao": _column_definition(key),
            "codigo": None,
            "fonte": "Open Data Brasil — contrato de exportação",
        }
        for key, value in (columns or {}).items()
    ]
    sources = [
        {
            "source_id": "dataset",
            "produtor": (dataset or {}).get("source_id"),
            "url": (dataset or {}).get("reference_url") or indicator.get("reference_url"),
            "edicao": None,
            "secao": None,
            "afirmacao": "Fonte do indicador exportado",
            "licenca": (dataset or {}).get("license_id"),
        }
    ]
    methods = [
        {
            "method_id": "exportacao_periodos_separados_v1",
            "tipo": "operacao_portal",
            "definicao": "Consulta das observações do release fixado pelos filtros indicados",
            "metodo": "Períodos separados; acumulados visuais não aplicados ao arquivo.",
            "universo": "Recorte exportado",
            "limites": "Sem nova regra de agregação",
            "lacunas": None,
        }
    ]
    if documentation:
        sources.extend(
            {
                "source_id": f"dataset:{link['dataset']}:v{link['variavel']}",
                "produtor": link["fonte_produtora"],
                "url": link["referencia_url"],
                "edicao": link["disponibilidade_fonte"],
                "secao": link["titulo_tabela"],
                "afirmacao": link["notas_fonte"],
                "licenca": link["licenca"],
            }
            for link in documentation.links
        )
        dictionary.extend(
            {
                "campo": f"tabela:{c['tabela']}/c{c['classificacao']}",
                "tipo": "codigo_documentado_na_fonte",
                "definicao": f"{c['nome_oficial']}: {c['definicao_oficial']}",
                "codigo": c["codigo"],
                "fonte": c["fonte"],
            }
            for c in documentation.codes
        )
        for method in documentation.methods:
            methods.append(
                {
                    "method_id": method["id"],
                    "tipo": "sintese_documental_parcial",
                    "definicao": method["conceito"],
                    "metodo": method["metodo"],
                    "universo": method["universo"],
                    "limites": method["limites"],
                    "lacunas": method["lacunas"],
                }
            )
            sources.extend(
                {
                    "source_id": f"{method['id']}:{i}",
                    "produtor": "Referência oficial",
                    "url": source["url"],
                    "edicao": source.get("edicao"),
                    "secao": source.get("secao"),
                    "afirmacao": source.get("afirmacao_sustentada"),
                    "licenca": None,
                }
                for i, source in enumerate(method["fontes"], 1)
            )
    return {
        "aviso": (
            "Arquivo gerado pelo Open Data Brasil a partir do release Gold indicado. "
            "Os produtores oficiais e as referências estão em fontes. Operações e filtros "
            "aplicados constam dos metadados; a documentação conserva lacunas explícitas."
        ),
        "gerado_em": generated,
        "artifact": {
            "generator_name": "Open Data Brasil",
            "generator_url": "https://opendatabrasil.org",
            "generator_role": "geracao_do_arquivo",
            "generator_version": "1.0.0",
            "schema_version": "odb-export/1.0.0",
            "generated_at": generated,
        },
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
                "time_aggregation",
            )
        },
        "fonte": dict(dataset) if dataset else None,
        "filtros": dict(filters),
        "release": provenance.model_dump(),
        "linhas": rows,
        "blocos": list(blocks),
        "documentacao": document,
        "documentacao_status": "revisao_parcial" if documentation else "ficha_nao_localizada",
        "dicionario": dictionary,
        "fontes": sources,
        "metodos": methods,
        "precisao": "value_exact preserva o valor recebido; valor numérico é auxiliar. "
        "Não recupera precisão já perdida antes da exportação.",
        "operacoes_visuais": {
            "accumulate": False,
            "seasonal_sum": False,
            "nota": "Os períodos permanecem separados no arquivo.",
        },
        "legenda_status": {
            "valid": "valor publicado",
            "true_zero": "zero publicado",
            "rounded_zero": "zero por arredondamento",
            "derived_sum": "soma calculada a partir dos valores publicados",
            "partial_sum": "soma parcial dos componentes disponíveis; consulte as notas e métodos",
            "suppressed": "suprimido pela fonte (X): ausente, não é zero",
            "not_available": "não disponível (...)",
            "not_applicable": "não se aplica (..)",
            "absent": "combinação não publicada",
        },
    }


def _column_definition(column: str) -> str:
    """Definições do contrato; campos desconhecidos ficam sem interpretação inventada."""
    definitions = {
        "geography_key": "Chave territorial do release, com tipo de unidade.",
        "territorio": "Nome do território no release consultado.",
        "uf": "Sigla da UF quando aplicável; vazio não é uma UF inferida.",
        "periodo": "Período da observação; significado e calendário constam da ficha.",
        "valor": "Valor numérico auxiliar; use value_exact para preservar a representação decimal.",
        "value_exact": "Valor recebido como texto decimal, sem conversão para float.",
        "status": "Estado do valor; ausência e sigilo não equivalem a zero.",
        "unidade": "Unidade efetiva, incluindo correção de preços quando solicitada.",
        "source_table_id": "Tabela de origem informada pela observação; nulo se não disponível.",
        "block_id": "Bloco da consulta, vinculado a filtros, operações e proveniência em blocos.",
        "row_id": "Identificador único da linha neste arquivo.",
        "indicator_id": "Identificador do indicador semântico.",
        "kpi_id": "Identificador do KPI solicitado.",
        "release_id": "Release fixado para todas as partes do arquivo.",
        "nivel": "Nível territorial consultado.",
        "grao": "Grão temporal efetivamente consultado.",
        "tipo": "Publicado ou derivado conforme a consulta executada.",
    }
    if column.endswith("_code"):
        return (
            "Chave textual da categoria na classificação indicada; o rótulo sai em coluna própria."
        )
    if column.endswith("_category_key"):
        return "Chave da categoria no release, com identificador da classificação."
    return definitions.get(column, "Rótulo de categoria da dimensão; códigos em coluna própria.")


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
        try:
            return render_workbook(data, meta)
        except WorkbookLimitError as exc:
            raise ExportTooLargeError(str(exc)) from exc
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("dados.csv", "﻿" + data.write_csv())
        archive.writestr("metadados.json", meta_json)
    return buffer.getvalue()
