"""Exportação de um release Gold publicado para análise local (§10.8, §19.3).

O pacote exportado é uma **cópia descartável**, não uma fonte oficial:

* só sai de um release publicado (ativo ou identificado), com as versões Delta
  fixadas no manifesto. Nunca de versões não publicadas;
* fica fora do lakehouse, numa pasta por release
  (``<destino>/<escopo>/<release_id>/``). A invalidação é por release: um
  release novo gera outra pasta, e as antigas podem ser apagadas a qualquer
  momento;
* traz ``manifest.json`` (release, versões, linhas e SHA-256 de cada arquivo)
  e ``LEIAME.txt`` (procedência, licença e aviso de cópia não oficial).

Conteúdo:

* ``parquet/<tabela>.parquet``: cada tabela Gold, com os tipos originais
  (valores em ``decimal(38,6)``);
* ``gold.duckdb``: as mesmas tabelas, mais a view ``observacoes`` (observações
  com nomes de indicador, território e desagregação e o valor em ``DOUBLE``,
  pronto para gráficos) e a view ``arvore_indicadores``. Feito para abrir no
  DBeaver ou em ``duckdb.connect(..., read_only=True)``.

A escrita é atômica: monta tudo numa pasta temporária e renomeia no fim.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import duckdb
import polars as pl

from odb_lakehouse import DeltaReader

EXPORT_FORMAT_VERSION = "1.0.0"
_TABLE_ID = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
MANIFEST = "manifest.json"

# View de análise: uma linha por observação, com rótulos e valor numérico.
OBSERVATIONS_VIEW = """
CREATE VIEW observacoes AS
SELECT
    o.indicator_id,
    i.name AS indicator_name,
    i.unit,
    i.additivity,
    o.dataset_id,
    o.source_table_id,
    o.source_variable_id,
    o.geography_key,
    o.level_id,
    g.level_name,
    g.territory_code,
    g.name AS territory_name,
    g.uf_code,
    g.uf_abbreviation,
    g.region_code,
    o.period,
    p.year,
    o.breakdown_key,
    b.label AS breakdown_label,
    b.non_total_count,
    o.value,
    CAST(o.value AS DOUBLE) AS value_double,
    o.value_status,
    o.value_raw,
    o.flags
FROM indicator_observation AS o
JOIN dim_indicator AS i USING (indicator_id)
JOIN dim_geography AS g USING (geography_key)
JOIN dim_breakdown AS b USING (breakdown_key)
JOIN dim_period AS p USING (period)
"""

TREE_VIEW = """
CREATE VIEW arvore_indicadores AS
SELECT repeat('  ', depth) || label AS item, node_type, indicator_id, classification_id,
       category_key, node_key, parent_key, sort_order
FROM dim_indicator_node
ORDER BY sort_order
"""


class ExportError(RuntimeError):
    """Exportação impossível ou recusada."""


class TableRef(Protocol):
    """Versão fixada de uma tabela (``odb_catalog.TableVersion`` atende)."""

    @property
    def table_id(self) -> str:
        """Identificador lógico da tabela."""
        ...

    @property
    def storage_uri(self) -> str:
        """URI da tabela Delta."""
        ...

    @property
    def delta_version(self) -> int:
        """Versão Delta publicada."""
        ...

    @property
    def contract_version(self) -> str:
        """Versão do contrato da tabela."""
        ...


@dataclass(frozen=True, slots=True)
class ReleaseToExport:
    """Release publicado a exportar."""

    release_id: str
    scope: str
    status: str
    activated_at: datetime | None
    tables: Mapping[str, TableRef]


@dataclass
class ExportResult:
    """Resultado da exportação."""

    path: Path
    release_id: str
    status: str  # "created" ou "existing"
    tables: dict[str, dict[str, Any]] = field(default_factory=dict)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _readme(release: ReleaseToExport, provenance: Mapping[str, Any]) -> str:
    sources = "\n".join(f"  - {s}" for s in provenance.get("sources", [])) or "  - (não informado)"
    return f"""OpenDataBrasil: exportação do release {release.release_id} (escopo {release.scope})

CÓPIA DESCARTÁVEL PARA ANÁLISE LOCAL. NÃO É FONTE OFICIAL.
A fonte oficial é a camada Gold em Delta Lake, nas versões listadas em manifest.json.
Esta pasta pode ser apagada a qualquer momento e recriada com `odb gold export`.

Licença: {provenance.get("license", "não informada")}
Situação da licença: {provenance.get("license_review_status", "desconhecida")}
  (requires_review = uso interno; não redistribua até a confirmação dos termos).
Cite a fonte original dos dados:
{sources}

Conteúdo:
  parquet/<tabela>.parquet   tabelas Gold com os tipos originais (valores decimal(38,6))
  gold.duckdb                as mesmas tabelas, mais as views `observacoes` e `arvore_indicadores`
  manifest.json              release, versões Delta, linhas e SHA-256 de cada arquivo

Regras de leitura (ADR-0008):
  - os totais de UF, Grande Região e Brasil são os oficiais; não some municípios para obtê-los;
  - indicadores `non_additive` (percentuais, densidade) não podem ser somados;
  - nas desagregações, filtre as demais classificações no Total
    (veja `breakdown_key` e `non_total_count`);
  - value_status diferente de valid/true_zero/rounded_zero significa valor ausente (não é zero).
"""


def export_release(
    release: ReleaseToExport,
    out_dir: Path,
    *,
    provenance: Mapping[str, Any] | None = None,
    force: bool = False,
    reader: DeltaReader | None = None,
) -> ExportResult:
    """Exporta as tabelas do release para ``out_dir/<escopo>/<release_id>``."""
    if release.status not in {"active", "superseded"}:
        msg = f"só releases publicados podem ser exportados (estado: {release.status})"
        raise ExportError(msg)
    if not release.tables:
        msg = f"release {release.release_id} sem tabelas"
        raise ExportError(msg)
    provenance = dict(provenance or {})
    reader = reader or DeltaReader()
    scope_dir = out_dir / release.scope
    target = scope_dir / release.release_id
    if target.exists() and not force:
        manifest = json.loads((target / MANIFEST).read_text(encoding="utf-8"))
        return ExportResult(target, release.release_id, "existing", dict(manifest["tables"]))
    if target.exists() and not (target / MANIFEST).is_file():
        msg = f"{target} existe e não é uma exportação (sem {MANIFEST}); nada foi apagado"
        raise ExportError(msg)

    scope_dir.mkdir(parents=True, exist_ok=True)
    staging = scope_dir / f".tmp-{release.release_id}-{uuid.uuid4().hex[:8]}"
    (staging / "parquet").mkdir(parents=True)
    try:
        tables: dict[str, dict[str, Any]] = {}
        for table_id, ref in sorted(release.tables.items()):
            frame = reader.scan(ref.storage_uri, ref.delta_version).collect()
            path = staging / "parquet" / f"{table_id}.parquet"
            frame.write_parquet(path, compression="zstd", statistics=True)
            tables[table_id] = {
                "file": f"parquet/{table_id}.parquet",
                "rows": frame.height,
                "sha256": _sha256(path),
                "storage_uri": ref.storage_uri,
                "delta_version": ref.delta_version,
                "contract_version": ref.contract_version,
            }
        _duckdb_file(staging, tables)
        manifest = {
            "export_format_version": EXPORT_FORMAT_VERSION,
            "release_id": release.release_id,
            "scope": release.scope,
            "release_status": release.status,
            "release_activated_at": release.activated_at,
            "exported_at": datetime.now(UTC),
            "official": False,
            "provenance": provenance,
            "tables": tables,
            "duckdb": {"file": "gold.duckdb", "sha256": _sha256(staging / "gold.duckdb")},
        }
        (staging / MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        (staging / "LEIAME.txt").write_text(_readme(release, provenance), encoding="utf-8")
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    (scope_dir / "latest.json").write_text(
        json.dumps(
            {
                "release_id": release.release_id,
                "path": release.release_id,
                "status": release.status,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return ExportResult(target, release.release_id, "created", tables)


def _duckdb_file(staging: Path, tables: Mapping[str, Mapping[str, Any]]) -> None:
    """Base DuckDB autocontida (sem caminhos externos), com as views de análise."""
    con = duckdb.connect(
        str(staging / "gold.duckdb"),
        config={"autoinstall_known_extensions": False, "autoload_known_extensions": False},
    )
    try:
        for table_id, info in tables.items():
            if not _TABLE_ID.fullmatch(table_id):
                msg = f"identificador de tabela inválido para a exportação: {table_id!r}"
                raise ExportError(msg)
            # Identificador validado acima; o caminho entra como parâmetro.
            con.execute(
                f'CREATE TABLE "{table_id}" AS SELECT * FROM read_parquet(?)',  # noqa: S608
                [str(staging / str(info["file"]))],
            )
        if {
            "indicator_observation",
            "dim_indicator",
            "dim_geography",
            "dim_breakdown",
            "dim_period",
        } <= set(tables):
            con.execute(OBSERVATIONS_VIEW)
        if "dim_indicator_node" in tables:
            con.execute(TREE_VIEW)
        con.execute("CHECKPOINT")
    finally:
        con.close()


def read_observations(path: Path) -> pl.LazyFrame:
    """Atalho para análise: observações de uma exportação como ``LazyFrame`` com rótulos."""
    base = path / "parquet"
    obs = pl.scan_parquet(base / "indicator_observation.parquet")
    ind = pl.scan_parquet(base / "dim_indicator.parquet").select(
        "indicator_id", pl.col("name").alias("indicator_name"), "additivity"
    )
    geo = pl.scan_parquet(base / "dim_geography.parquet").select(
        "geography_key",
        "territory_code",
        pl.col("name").alias("territory_name"),
        "uf_code",
        "uf_abbreviation",
    )
    brk = pl.scan_parquet(base / "dim_breakdown.parquet").select(
        "breakdown_key", pl.col("label").alias("breakdown_label"), "non_total_count"
    )
    return (
        obs.join(ind, on="indicator_id")
        .join(geo, on="geography_key")
        .join(brk, on="breakdown_key")
        .with_columns(pl.col("value").cast(pl.Float64).alias("value_double"))
    )
