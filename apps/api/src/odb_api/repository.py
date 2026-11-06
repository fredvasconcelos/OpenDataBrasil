"""Catálogo operacional no PostgreSQL (papel ``odb_reader``, só leitura).

Fontes, datasets e licenças vêm do schema ``catalog``. Os metadados dos
indicadores vêm do ``dim_indicator`` do release (``odb_api.gold``), para ficarem
coerentes com os dados consultados.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, text

_DATASETS = (
    "SELECT d.dataset_id, d.source_id, d.official_id, d.title, d.description, d.periodicity, "
    "d.reference_url, d.access_classification, l.license_id, l.name AS license_name, "
    "l.url AS license_url, l.conditions, l.review_status FROM catalog.dataset AS d "
    "JOIN catalog.license AS l USING (license_id) WHERE d.enabled"
)


class CatalogRepository:
    """Consultas parametrizadas ao catálogo."""

    def __init__(self, engine: Engine) -> None:
        """``engine`` conecta com o papel de leitura."""
        self._engine = engine

    def sources(self) -> list[dict[str, Any]]:
        """Fontes cadastradas."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT source_id, institution_id, name, connector_type, base_url, "
                    "documentation_url FROM catalog.source ORDER BY source_id"
                )
            )
            return [dict(r) for r in result.mappings()]

    def datasets(self, dataset_id: str | None = None) -> list[dict[str, Any]]:
        """Datasets habilitados, com a licença."""
        sql = _DATASETS
        params: dict[str, Any] = {}
        if dataset_id is not None:
            sql += " AND d.dataset_id = :id"
            params["id"] = dataset_id
        with self._engine.connect() as conn:
            result = conn.execute(text(sql + " ORDER BY d.dataset_id"), params)
            return [dict(r) for r in result.mappings()]

    def ping(self) -> None:
        """Confere a conexão."""
        with self._engine.connect() as conn:
            conn.execute(text("SELECT 1"))
