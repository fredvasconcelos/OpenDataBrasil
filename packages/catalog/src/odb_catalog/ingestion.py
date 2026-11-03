"""Implementação PostgreSQL de ``odb_ingestion.IngestionRegistry``."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from odb_ingestion.config import SourceCatalog
from odb_ingestion.contract import PartitionState, Watermark
from odb_ingestion.runner import ArtifactRecord, DuplicateContentError, StoredArtifact

_STORED_UQ = "bronze_artifact_stored_checksum_uq"


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


class PostgresIngestionRegistry:
    """Metadados de ingestão nos schemas ``catalog`` e ``operations``."""

    def __init__(self, engine: Engine) -> None:
        """Usa o engine informado (role ``odb_pipeline`` em produção)."""
        self._engine = engine

    def sync_catalog(self, catalog: SourceCatalog) -> None:
        """Upsert idempotente de todas as entidades configuradas."""
        with self._engine.begin() as conn:
            for inst in catalog.institutions.values():
                conn.execute(
                    text(
                        "INSERT INTO catalog.institution (institution_id, name, acronym, url) "
                        "VALUES (:id, :name, :acr, :url) ON CONFLICT (institution_id) DO UPDATE "
                        "SET name = EXCLUDED.name, acronym = EXCLUDED.acronym, url = EXCLUDED.url, "
                        "updated_at = now()"
                    ),
                    {"id": inst.id, "name": inst.name, "acr": inst.acronym, "url": inst.url},
                )
            for lic in catalog.licenses.values():
                conn.execute(
                    text(
                        "INSERT INTO catalog.license (license_id, name, url, conditions, "
                        "review_status, notes) VALUES (:id, :name, :url, :cond, :rs, :notes) "
                        "ON CONFLICT (license_id) DO UPDATE SET name = EXCLUDED.name, "
                        "url = EXCLUDED.url, conditions = EXCLUDED.conditions, "
                        "review_status = EXCLUDED.review_status, notes = EXCLUDED.notes, "
                        "updated_at = now()"
                    ),
                    {
                        "id": lic.id,
                        "name": lic.name,
                        "url": lic.url,
                        "cond": lic.conditions,
                        "rs": lic.review_status,
                        "notes": lic.notes,
                    },
                )
            for src in catalog.sources.values():
                conn.execute(
                    text(
                        "INSERT INTO catalog.source (source_id, institution_id, name, "
                        "connector_type, base_url, documentation_url) "
                        "VALUES (:id, :inst, :name, :ct, :url, :doc) "
                        "ON CONFLICT (source_id) DO UPDATE SET institution_id = "
                        "EXCLUDED.institution_id, "
                        "name = EXCLUDED.name, connector_type = EXCLUDED.connector_type, "
                        "base_url = EXCLUDED.base_url, "
                        "documentation_url = EXCLUDED.documentation_url, "
                        "updated_at = now()"
                    ),
                    {
                        "id": src.id,
                        "inst": catalog.source_institution[src.id],
                        "name": src.name,
                        "ct": src.connector,
                        "url": src.base_url,
                        "doc": src.documentation_url,
                    },
                )
            for ds in catalog.datasets.values():
                conn.execute(
                    text(
                        "INSERT INTO catalog.dataset (dataset_id, source_id, official_id, title, "
                        "description, license_id, access_classification, periodicity, "
                        "reference_url, enabled, config, config_sha256) VALUES (:id, :src, :oid, "
                        ":title, :desc, :lic, :acc, :per, :ref, :en, CAST(:cfg AS jsonb), :sha) "
                        "ON CONFLICT (dataset_id) DO UPDATE SET source_id = EXCLUDED.source_id, "
                        "official_id = EXCLUDED.official_id, title = EXCLUDED.title, "
                        "description = EXCLUDED.description, license_id = EXCLUDED.license_id, "
                        "access_classification = EXCLUDED.access_classification, "
                        "periodicity = EXCLUDED.periodicity, "
                        "reference_url = EXCLUDED.reference_url, "
                        "enabled = EXCLUDED.enabled, config = EXCLUDED.config, "
                        "config_sha256 = EXCLUDED.config_sha256, updated_at = now() "
                        "WHERE catalog.dataset.config_sha256 <> EXCLUDED.config_sha256"
                    ),
                    {
                        "id": ds.id,
                        "src": ds.source,
                        "oid": ds.official_id,
                        "title": ds.title,
                        "desc": ds.description,
                        "lic": ds.license,
                        "acc": ds.access_classification,
                        "per": ds.periodicity,
                        "ref": ds.reference_url,
                        "en": ds.enabled,
                        "cfg": _j(ds.model_dump(mode="json")),
                        "sha": ds.config_sha256(),
                    },
                )

    def start_ingestion(
        self, ingestion_id: str, dataset_id: str, run_id: str | None, parameters: Mapping[str, Any]
    ) -> None:
        """Registra a ingestão em ``running``."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO operations.ingestion (ingestion_id, run_id, dataset_id, status, "
                    "parameters) VALUES (:id, :run, :ds, 'running', CAST(:p AS jsonb))"
                ),
                {"id": ingestion_id, "run": run_id, "ds": dataset_id, "p": _j(parameters)},
            )

    def save_plan(self, ingestion_id: str, plan: Mapping[str, Any]) -> None:
        """Guarda o plano serializado."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE operations.ingestion SET plan = CAST(:p AS jsonb) WHERE ingestion_id "
                    "= :id"
                ),
                {"id": ingestion_id, "p": _j(plan)},
            )

    def find_stored(self, checksum_sha256: str) -> StoredArtifact | None:
        """Artefato ``stored`` com o mesmo SHA-256."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT artifact_id::text, storage_uri FROM operations.bronze_artifact "
                    "WHERE checksum_sha256 = :sha AND ingestion_status = 'stored'"
                ),
                {"sha": checksum_sha256},
            ).first()
        return StoredArtifact(row[0], row[1]) if row else None

    def record_artifact(self, record: ArtifactRecord) -> None:
        """Insere o artefato. Conflito de deduplicação vira ``DuplicateContentError``."""
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO operations.bronze_artifact (artifact_id, ingestion_id, "
                        "dataset_id, partition_key, source_url, retrieved_at, http_status, "
                        "content_type, file_size_bytes, checksum_sha256, storage_uri, reused_from, "
                        "source_version, reference_period, license_id, access_classification, "
                        "ingestion_status, validation, response_headers, error) VALUES (:aid, "
                        ":iid, "
                        ":ds, :pk, :url, :at, :hs, :ct, :size, :sha, :uri, :reused, :sv, :rp, "
                        ":lic, "
                        ":acc, :st, CAST(:val AS jsonb), CAST(:hdr AS jsonb), :err)"
                    ),
                    {
                        "aid": record.artifact_id,
                        "iid": record.ingestion_id,
                        "ds": record.dataset_id,
                        "pk": record.partition_key,
                        "url": record.source_url,
                        "at": record.retrieved_at,
                        "hs": record.http_status,
                        "ct": record.content_type,
                        "size": record.file_size_bytes,
                        "sha": record.checksum_sha256,
                        "uri": record.storage_uri,
                        "reused": record.reused_from,
                        "sv": record.source_version,
                        "rp": record.reference_period,
                        "lic": record.license_id,
                        "acc": record.access_classification,
                        "st": record.status,
                        "val": _j(record.validation),
                        "hdr": _j(record.response_headers),
                        "err": record.error,
                    },
                )
        except IntegrityError as exc:
            if _STORED_UQ in str(exc.orig):
                raise DuplicateContentError(str(exc.orig)) from exc
            raise

    def get_watermark(self, dataset_id: str) -> Watermark:
        """Estado das partições."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT partition_key, checksum_sha256, etag, last_modified, source_version "
                    "FROM operations.watermark WHERE dataset_id = :ds"
                ),
                {"ds": dataset_id},
            ).all()
        return Watermark(
            partitions={
                r[0]: PartitionState(
                    checksum_sha256=r[1], etag=r[2], last_modified=r[3], source_version=r[4]
                )
                for r in rows
            }
        )

    def update_watermark(
        self, dataset_id: str, partitions: Mapping[str, tuple[PartitionState, str | None]]
    ) -> None:
        """Upsert de todas as partições numa única transação."""
        with self._engine.begin() as conn:
            for key, (state, artifact_id) in partitions.items():
                conn.execute(
                    text(
                        "INSERT INTO operations.watermark (dataset_id, partition_key, "
                        "checksum_sha256, artifact_id, source_version, etag, last_modified) "
                        "VALUES (:ds, :pk, :sha, :aid, :sv, :etag, :lm) "
                        "ON CONFLICT (dataset_id, partition_key) DO UPDATE SET "
                        "checksum_sha256 = EXCLUDED.checksum_sha256, "
                        "artifact_id = EXCLUDED.artifact_id, "
                        "source_version = EXCLUDED.source_version, etag = EXCLUDED.etag, "
                        "last_modified = EXCLUDED.last_modified, updated_at = now()"
                    ),
                    {
                        "ds": dataset_id,
                        "pk": key,
                        "sha": state.checksum_sha256,
                        "aid": artifact_id,
                        "sv": state.source_version,
                        "etag": state.etag,
                        "lm": state.last_modified,
                    },
                )

    def finish_ingestion(
        self,
        ingestion_id: str,
        status: Literal["succeeded", "failed"],
        stats: Mapping[str, Any],
        error: str | None,
    ) -> None:
        """Marca o fim da ingestão."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE operations.ingestion SET status = :st, finished_at = now(), "
                    "stats = CAST(:stats AS jsonb), error = :err WHERE ingestion_id = :id"
                ),
                {
                    "id": ingestion_id,
                    "st": status,
                    "stats": _j(stats),
                    "err": (error or None) and error[:4000],
                },
            )

    def recent_ingestions(
        self, dataset_id: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Últimas ingestões com contagens por estado (para ``odb ingest status``)."""
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT i.ingestion_id::text, i.dataset_id, i.status, i.started_at, "
                        "i.finished_at, i.stats, i.error FROM operations.ingestion i "
                        "WHERE (CAST(:ds AS text) IS NULL OR i.dataset_id = :ds) "
                        "ORDER BY i.started_at DESC LIMIT :lim"
                    ),
                    {"ds": dataset_id, "lim": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
