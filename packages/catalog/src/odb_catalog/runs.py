"""Registro de execuções em ``operations.pipeline_run``."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, text


@contextmanager
def tracked_run(
    engine: Engine, command: str, code_version: str, parameters: Mapping[str, Any] | None = None
) -> Iterator[str]:
    """Registra a execução como ``running`` e a finaliza conforme o resultado.

    Uma falha marca ``failed`` com a mensagem e propaga a exceção. Cargas
    incompletas nunca são registradas como concluídas (§7.5).
    """
    run_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO operations.pipeline_run (run_id, command, status, code_version, "
                "parameters) VALUES (:id, :cmd, 'running', :cv, CAST(:params AS jsonb))"
            ),
            {
                "id": run_id,
                "cmd": command,
                "cv": code_version,
                "params": json.dumps(parameters or {}),
            },
        )
    try:
        yield run_id
    except BaseException as exc:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE operations.pipeline_run SET status = 'failed', finished_at = now(), "
                    "error = :err WHERE run_id = :id"
                ),
                {"id": run_id, "err": f"{type(exc).__name__}: {exc}"[:4000]},
            )
        raise
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE operations.pipeline_run SET status = 'succeeded', finished_at = now() "
                "WHERE run_id = :id"
            ),
            {"id": run_id},
        )
