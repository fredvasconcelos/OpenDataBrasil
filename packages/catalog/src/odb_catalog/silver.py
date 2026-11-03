"""Implementação PostgreSQL de ``odb_processing.silver.SilverRegistry``."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Engine, text

from odb_processing.quality import CheckResult
from odb_processing.silver import PreviousRun, SilverInput, SilverRun


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


class PostgresSilverRegistry:
    """Entradas Bronze vigentes, execuções e resultados de qualidade."""

    def __init__(self, engine: Engine) -> None:
        """Usa o engine informado (role ``odb_pipeline`` em produção)."""
        self._engine = engine

    def current_inputs(self, dataset_id: str) -> list[SilverInput]:
        """Watermark → artefato que contém os bytes (o original ``stored``)."""
        sql = text(
            """
            SELECT w.partition_key, src.artifact_id::text, src.ingestion_id::text,
                   src.storage_uri, src.checksum_sha256, src.source_url, src.retrieved_at,
                   src.reference_period
            FROM operations.watermark w
            JOIN operations.bronze_artifact a ON a.artifact_id = w.artifact_id
            JOIN operations.bronze_artifact src
              ON src.artifact_id = COALESCE(a.reused_from, a.artifact_id)
            WHERE w.dataset_id = :ds AND src.ingestion_status = 'stored'
            ORDER BY w.partition_key
            """
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql, {"ds": dataset_id}).all()
        return [
            SilverInput(
                partition_key=r[0],
                artifact_id=r[1],
                ingestion_id=r[2],
                storage_uri=r[3],
                checksum_sha256=r[4],
                source_url=r[5],
                retrieved_at=r[6],
                reference_period=r[7],
            )
            for r in rows
        ]

    def last_success(self, dataset_id: str) -> PreviousRun | None:
        """Execução Silver mais recente com versão Delta válida."""
        sql = text(
            """
            SELECT run_id::text, input_fingerprint, target_uri, delta_version
            FROM operations.transformation_run
            WHERE dataset_id = :ds AND layer = 'silver' AND status IN ('succeeded', 'skipped')
            ORDER BY started_at DESC LIMIT 1
            """
        )
        with self._engine.connect() as conn:
            row = conn.execute(sql, {"ds": dataset_id}).first()
        if row is None:
            return None
        return PreviousRun(row[0], row[1], row[2], None if row[3] is None else int(row[3]))

    def start_run(
        self, run: SilverRun, *, pipeline_run_id: str | None, inputs: Sequence[SilverInput]
    ) -> None:
        """Registra a execução em ``running``."""
        payload = [
            {
                "partition_key": i.partition_key,
                "artifact_id": i.artifact_id,
                "checksum_sha256": i.checksum_sha256,
            }
            for i in inputs
        ]
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO operations.transformation_run (run_id, pipeline_run_id, "
                    "dataset_id, layer, target_uri, contract, contract_version, code_version, "
                    "input_fingerprint, inputs, status) VALUES (:id, :prid, :ds, 'silver', :uri, "
                    ":c, :cv, :code, :fp, CAST(:inputs AS jsonb), 'running')"
                ),
                {
                    "id": run.run_id,
                    "prid": pipeline_run_id,
                    "ds": run.dataset_id,
                    "uri": run.target_uri,
                    "c": run.contract,
                    "cv": run.contract_version,
                    "code": run.code_version,
                    "fp": run.input_fingerprint,
                    "inputs": _j(payload),
                },
            )

    def finish_run(self, run: SilverRun) -> None:
        """Finaliza a execução."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE operations.transformation_run SET status = :st, delta_version = :v, "
                    "stats = CAST(:stats AS jsonb), error = :err, finished_at = now() "
                    "WHERE run_id = :id"
                ),
                {
                    "id": run.run_id,
                    "st": run.status,
                    "v": run.delta_version,
                    "stats": _j(run.stats()),
                    "err": run.error and run.error[:4000],
                },
            )

    def record_checks(self, run_id: str, dataset_id: str, results: Sequence[CheckResult]) -> None:
        """Insere os resultados de qualidade da execução."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO quality.check_result (run_id, dataset_id, check_id, status, "
                    "message, observed, expected, details) VALUES (:run, :ds, :cid, :st, :msg, "
                    "CAST(:obs AS jsonb), CAST(:exp AS jsonb), CAST(:det AS jsonb))"
                ),
                [
                    {
                        "run": run_id,
                        "ds": dataset_id,
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

    def latest_report(self, dataset_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Última execução que rodou verificações e seus resultados (``odb quality report``)."""
        with self._engine.connect() as conn:
            run = (
                conn.execute(
                    text(
                        "SELECT r.run_id::text, r.status, r.delta_version, r.started_at, r.error, "
                        "r.contract, r.contract_version FROM operations.transformation_run r "
                        "WHERE r.dataset_id = :ds AND EXISTS (SELECT 1 FROM quality.check_result c "
                        "WHERE c.run_id = r.run_id) ORDER BY r.started_at DESC LIMIT 1"
                    ),
                    {"ds": dataset_id},
                )
                .mappings()
                .first()
            )
            if run is None:
                return None, []
            checks = (
                conn.execute(
                    text(
                        "SELECT check_id, status, message, observed, details "
                        "FROM quality.check_result WHERE run_id = :id ORDER BY result_id"
                    ),
                    {"id": run["run_id"]},
                )
                .mappings()
                .all()
            )
        return dict(run), [dict(c) for c in checks]
