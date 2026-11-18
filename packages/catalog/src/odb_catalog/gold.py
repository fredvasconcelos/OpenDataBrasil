"""Implementação PostgreSQL de ``odb_modeling.builder.GoldRegistry`` e catálogo de indicadores."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import polars as pl
from sqlalchemy import Engine, text

from odb_catalog.silver import PostgresSilverRegistry
from odb_modeling.builder import GoldBuild, GoldTable, PreviousGoldBuild
from odb_processing.quality import CheckResult
from odb_processing.silver import PreviousRun


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _tables_json(tables: Mapping[str, GoldTable]) -> dict[str, dict[str, Any]]:
    return {
        t.table_id: {
            "storage_uri": t.storage_uri,
            "delta_version": t.delta_version,
            "contract_version": t.contract_version,
            "rows": t.rows,
        }
        for t in tables.values()
    }


class PostgresGoldRegistry:
    """Construções Gold, resultados de qualidade e sincronização de ``catalog.indicator``."""

    def __init__(self, engine: Engine) -> None:
        """Usa o engine informado (role ``odb_pipeline`` em produção)."""
        self._engine = engine
        self._silver = PostgresSilverRegistry(engine)

    def silver_success(self, dataset_id: str) -> PreviousRun | None:
        """Última execução Silver válida do dataset."""
        return self._silver.last_success(dataset_id)

    def published_version(self, storage_uri: str) -> int | None:
        """Maior versão Delta da tabela fixada em algum release validado, ativo ou antigo."""
        sql = text(
            "SELECT max(rt.delta_version) FROM publication.release_table rt "
            "JOIN publication.release r USING (release_id) "
            "WHERE rt.storage_uri = :u AND r.status IN ('validated', 'active', 'superseded')"
        )
        with self._engine.connect() as conn:
            value = conn.execute(sql, {"u": storage_uri}).scalar()
        return None if value is None else int(value)

    def last_success(self, scope: str) -> PreviousGoldBuild | None:
        """Construção Gold mais recente com tabelas válidas."""
        sql = text(
            "SELECT build_id::text, input_fingerprint, tables FROM operations.gold_build "
            "WHERE scope = :s AND status IN ('succeeded', 'skipped') "
            "ORDER BY started_at DESC LIMIT 1"
        )
        with self._engine.connect() as conn:
            row = conn.execute(sql, {"s": scope}).first()
        if row is None:
            return None
        tables = {
            tid: GoldTable(
                table_id=tid,
                storage_uri=t["storage_uri"],
                delta_version=int(t["delta_version"]),
                contract_version=t["contract_version"],
                rows=t.get("rows"),
            )
            for tid, t in dict(row[2]).items()
        }
        return PreviousGoldBuild(row[0], row[1], tables)

    def start_build(self, build: GoldBuild, *, pipeline_run_id: str | None) -> None:
        """Registra a construção em ``running``."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO operations.gold_build (build_id, pipeline_run_id, scope, "
                    "config_version, code_version, input_fingerprint, inputs, status) VALUES "
                    "(:id, :prid, :s, :cfg, :code, :fp, CAST(:inputs AS jsonb), 'running')"
                ),
                {
                    "id": build.build_id,
                    "prid": pipeline_run_id,
                    "s": build.scope,
                    "cfg": build.config_version,
                    "code": build.code_version,
                    "fp": build.input_fingerprint,
                    "inputs": _j(build.inputs),
                },
            )

    def finish_build(self, build: GoldBuild) -> None:
        """Finaliza a construção."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE operations.gold_build SET status = :st, tables = CAST(:t AS jsonb), "
                    "stats = CAST(:stats AS jsonb), error = :err, finished_at = now() "
                    "WHERE build_id = :id"
                ),
                {
                    "id": build.build_id,
                    "st": build.status,
                    "t": _j(_tables_json(build.tables) if build.status != "failed" else {}),
                    "stats": _j(build.stats()),
                    "err": build.error and build.error[:4000],
                },
            )

    def record_checks(self, build_id: str, scope: str, results: Sequence[CheckResult]) -> None:
        """Insere os resultados de qualidade da construção."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO quality.gold_check_result (build_id, scope, check_id, status, "
                    "message, observed, expected, details) VALUES (:b, :s, :cid, :st, :msg, "
                    "CAST(:obs AS jsonb), CAST(:exp AS jsonb), CAST(:det AS jsonb))"
                ),
                [
                    {
                        "b": build_id,
                        "s": scope,
                        "cid": r.check_id,
                        "st": r.status.value,
                        "msg": r.message,
                        "obs": _j(r.observed),
                        "exp": _j(r.expected),
                        "det": _j(dict(r.details)),
                    }
                    for r in results
                ],
            )

    def link_release(self, build_id: str, release_id: str) -> None:
        """Associa a construção ao release criado com as suas versões."""
        with self._engine.begin() as conn:
            conn.execute(
                text("UPDATE operations.gold_build SET release_id = :r WHERE build_id = :b"),
                {"r": release_id, "b": build_id},
            )

    def sync_indicators(
        self, scope: str, config_version: str, build_id: str, indicators: pl.DataFrame
    ) -> int:
        """Atualiza ``catalog.indicator`` a partir de ``dim_indicator`` da construção."""
        rows = [
            {
                "id": r["indicator_id"],
                "scope": scope,
                "name": r["name"],
                "description": r["description"],
                "ds": r["dataset_id"],
                "var": r["source_variable_id"],
                "unit": r["unit"],
                "add": r["additivity"],
                "concept": r["concept"],
                "fact": r["fact_table"],
                "path": list(r["theme_path"]),
                "classes": list(r["classification_ids"]),
                "levels": list(r["available_levels"]),
                "periods": list(r["periods"]),
                "caveats": list(r["caveats"]),
                "inc": _j(list(r["incompatible_with"])),
                "cfg": config_version,
                "build": build_id,
            }
            for r in indicators.iter_rows(named=True)
        ]
        if not rows:
            return 0
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO catalog.indicator (indicator_id, scope, name, description,
                        dataset_id, source_variable_id, unit, additivity, concept, fact_table,
                        theme_path, classification_ids, available_levels, periods, caveats,
                        incompatible_with, config_version, last_build_id, updated_at)
                    VALUES (:id, :scope, :name, :description, :ds, :var, :unit, :add, :concept,
                        :fact, :path, :classes, :levels, :periods, :caveats,
                        CAST(:inc AS jsonb), :cfg, :build, now())
                    ON CONFLICT (indicator_id) DO UPDATE SET
                        scope = EXCLUDED.scope, name = EXCLUDED.name,
                        description = EXCLUDED.description, dataset_id = EXCLUDED.dataset_id,
                        source_variable_id = EXCLUDED.source_variable_id, unit = EXCLUDED.unit,
                        additivity = EXCLUDED.additivity, concept = EXCLUDED.concept,
                        fact_table = EXCLUDED.fact_table, theme_path = EXCLUDED.theme_path,
                        classification_ids = EXCLUDED.classification_ids,
                        available_levels = EXCLUDED.available_levels,
                        periods = EXCLUDED.periods, caveats = EXCLUDED.caveats,
                        incompatible_with = EXCLUDED.incompatible_with,
                        config_version = EXCLUDED.config_version,
                        last_build_id = EXCLUDED.last_build_id, updated_at = now()
                    """
                ),
                rows,
            )
        return len(rows)

    def latest_report(self, scope: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Última construção com verificações e os resultados (``odb quality gold``)."""
        with self._engine.connect() as conn:
            build = (
                conn.execute(
                    text(
                        "SELECT b.build_id::text, b.status, b.started_at, b.error, "
                        "b.release_id::text FROM operations.gold_build b WHERE b.scope = :s "
                        "AND EXISTS (SELECT 1 FROM quality.gold_check_result c "
                        "WHERE c.build_id = b.build_id) ORDER BY b.started_at DESC LIMIT 1"
                    ),
                    {"s": scope},
                )
                .mappings()
                .first()
            )
            if build is None:
                return None, []
            checks = (
                conn.execute(
                    text(
                        "SELECT check_id, status, message, observed, details "
                        "FROM quality.gold_check_result WHERE build_id = :b ORDER BY result_id"
                    ),
                    {"b": build["build_id"]},
                )
                .mappings()
                .all()
            )
        return dict(build), [dict(c) for c in checks]
