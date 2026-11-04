"""Publicação transacional de releases (§10.9, §12.6, §17.2).

Ciclo de vida::

    draft ──validate()──▶ validated ──activate()──▶ active ──(novo ativo)──▶ superseded
      └──────────────▶ failed ◀───────────────┘

* ``validate`` confere qualidade e existência de cada versão Delta e congela o
  manifesto;
* ``activate`` roda numa única transação PostgreSQL: trava o release e o
  escopo, troca o ativo anterior para ``superseded``, ativa o novo e verifica
  de novo as versões no log Delta. Qualquer falha desfaz tudo, e o release
  anterior continua vigente. Depois, a falha é registrada em transação própria;
* o índice único parcial garante no máximo um release ativo por escopo.

Delta e PostgreSQL não compartilham transação. A escrita Delta precede o
release, e a "publicação" é só a ativação do ponteiro no PostgreSQL (publicação
em duas etapas).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol

from sqlalchemy import Connection, Engine, text

QualityStatus = Literal["passed", "failed", "not_run"]
ReleaseStatus = Literal["draft", "validated", "active", "superseded", "failed"]


class PublicationError(RuntimeError):
    """Transição de publicação rejeitada."""


class VersionVerifier(Protocol):
    """Confirma que uma versão Delta existe e pode ser lida (``DeltaReader`` atende)."""

    def has_version(self, table_uri: str, version: int) -> bool:
        """Retorna True se a versão estiver disponível."""
        ...


@dataclass(frozen=True, slots=True)
class TableVersion:
    """Versão de uma tabela lógica incluída em um release."""

    table_id: str
    storage_uri: str
    delta_version: int
    contract_version: str
    quality_status: QualityStatus = "passed"


@dataclass(frozen=True, slots=True)
class Release:
    """Estado de um release lido do catálogo."""

    release_id: str
    scope: str
    status: ReleaseStatus
    code_version: str
    manifest: dict[str, Any]
    tables: dict[str, TableVersion] = field(default_factory=dict)
    activated_at: datetime | None = None
    failure_reason: str | None = None


_SELECT_RELEASE = """
    SELECT release_id::text, scope, status, code_version, manifest, activated_at, failure_reason
    FROM publication.release
"""


class PublicationService:
    """Operações de publicação sobre o schema ``publication``."""

    def __init__(self, engine: Engine, verifier: VersionVerifier, actor: str) -> None:
        """``actor`` identifica o processo ou responsável registrado nos eventos."""
        self._engine = engine
        self._verifier = verifier
        self._actor = actor

    # ------------------------------------------------------------- leitura

    @staticmethod
    def _load(conn: Connection, where: str, params: dict[str, Any]) -> Release | None:
        row = conn.execute(text(_SELECT_RELEASE + where), params).mappings().first()
        if row is None:
            return None
        tables = {
            t["table_id"]: TableVersion(
                table_id=t["table_id"],
                storage_uri=t["storage_uri"],
                delta_version=int(t["delta_version"]),
                contract_version=t["contract_version"],
                quality_status=t["quality_status"],
            )
            for t in conn.execute(
                text(
                    "SELECT table_id, storage_uri, delta_version, contract_version, quality_status "
                    "FROM publication.release_table WHERE release_id = :id ORDER BY table_id"
                ),
                {"id": row["release_id"]},
            ).mappings()
        }
        return Release(
            release_id=row["release_id"],
            scope=row["scope"],
            status=row["status"],
            code_version=row["code_version"],
            manifest=dict(row["manifest"]),
            tables=tables,
            activated_at=row["activated_at"],
            failure_reason=row["failure_reason"],
        )

    def get(self, release_id: str) -> Release:
        """Release por identificador (inclusive os substituídos, para reprodutibilidade)."""
        with self._engine.connect() as conn:
            release = self._load(conn, "WHERE release_id = :id", {"id": release_id})
        if release is None:
            msg = f"release inexistente: {release_id}"
            raise PublicationError(msg)
        return release

    def active(self, scope: str) -> Release | None:
        """Release vigente do escopo, se houver."""
        with self._engine.connect() as conn:
            return self._load(conn, "WHERE scope = :s AND status = 'active'", {"s": scope})

    def list_releases(self, scope: str | None = None, limit: int = 20) -> list[Release]:
        """Releases mais recentes (de um escopo ou de todos)."""
        where = "WHERE scope = :s " if scope else ""
        with self._engine.connect() as conn:
            ids = (
                conn.execute(
                    text(
                        f"SELECT release_id::text FROM publication.release {where}"  # noqa: S608
                        "ORDER BY created_at DESC LIMIT :n"
                    ),
                    {"s": scope, "n": limit},
                )
                .scalars()
                .all()
            )
            releases = [self._load(conn, "WHERE release_id = :id", {"id": i}) for i in ids]
        return [r for r in releases if r is not None]

    def resolve(self, scope: str, table_id: str) -> TableVersion:
        """Versão autorizada de uma tabela lógica no release vigente."""
        release = self.active(scope)
        if release is None:
            msg = f"nenhum release ativo para o escopo {scope!r}"
            raise PublicationError(msg)
        try:
            return release.tables[table_id]
        except KeyError as exc:
            msg = f"tabela {table_id!r} não publicada no escopo {scope!r}"
            raise PublicationError(msg) from exc

    # ------------------------------------------------------------- escrita

    def _event(
        self,
        conn: Connection,
        release_id: str,
        from_status: str | None,
        to_status: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            text(
                "INSERT INTO publication.release_event "
                "(release_id, from_status, to_status, actor, detail) "
                "VALUES (:id, :f, :t, :a, CAST(:d AS jsonb))"
            ),
            {
                "id": release_id,
                "f": from_status,
                "t": to_status,
                "a": self._actor,
                "d": json.dumps(detail or {}),
            },
        )

    def create_draft(self, scope: str, code_version: str, tables: Sequence[TableVersion]) -> str:
        """Cria um release em ``draft`` com as versões informadas."""
        if not tables:
            msg = "release exige ao menos uma tabela"
            raise PublicationError(msg)
        ids = [t.table_id for t in tables]
        if len(set(ids)) != len(ids):
            msg = f"table_id repetido no release: {ids}"
            raise PublicationError(msg)
        release_id = str(uuid.uuid4())
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO publication.release (release_id, scope, code_version, created_by) "
                    "VALUES (:id, :scope, :cv, :by)"
                ),
                {"id": release_id, "scope": scope, "cv": code_version, "by": self._actor},
            )
            conn.execute(
                text(
                    "INSERT INTO publication.release_table (release_id, table_id, storage_uri, "
                    "delta_version, contract_version, quality_status) "
                    "VALUES (:id, :tid, :uri, :v, :cv, :q)"
                ),
                [
                    {
                        "id": release_id,
                        "tid": t.table_id,
                        "uri": t.storage_uri,
                        "v": t.delta_version,
                        "cv": t.contract_version,
                        "q": t.quality_status,
                    }
                    for t in tables
                ],
            )
            self._event(conn, release_id, None, "draft")
        return release_id

    def _problems(self, release: Release) -> list[str]:
        problems = [
            f"{t.table_id}: qualidade {t.quality_status}"
            for t in release.tables.values()
            if t.quality_status != "passed"
        ]
        problems.extend(
            f"{t.table_id}: versão {t.delta_version} indisponível em {t.storage_uri}"
            for t in release.tables.values()
            if not self._verifier.has_version(t.storage_uri, t.delta_version)
        )
        return problems

    def _fail(self, release_id: str, from_status: str, reason: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE publication.release SET status = 'failed', failure_reason = :r "
                    "WHERE release_id = :id AND status = :f"
                ),
                {"id": release_id, "r": reason[:4000], "f": from_status},
            )
            self._event(conn, release_id, from_status, "failed", {"reason": reason[:4000]})

    def validate(self, release_id: str) -> Release:
        """``draft`` → ``validated`` (manifesto congelado) ou ``failed``."""
        release = self.get(release_id)
        if release.status != "draft":
            msg = f"apenas releases em draft podem ser validados (atual: {release.status})"
            raise PublicationError(msg)
        problems = self._problems(release)
        if problems:
            reason = "; ".join(problems)
            self._fail(release_id, "draft", reason)
            msg = f"validação falhou: {reason}"
            raise PublicationError(msg)
        manifest = {
            "release_id": release.release_id,
            "scope": release.scope,
            "code_version": release.code_version,
            "tables": [
                {
                    "table_id": t.table_id,
                    "storage_uri": t.storage_uri,
                    "delta_version": t.delta_version,
                    "contract_version": t.contract_version,
                    "quality_status": t.quality_status,
                }
                for t in release.tables.values()
            ],
        }
        with self._engine.begin() as conn:
            updated = conn.execute(
                text(
                    "UPDATE publication.release SET status = 'validated', validated_at = now(), "
                    "manifest = CAST(:m AS jsonb) WHERE release_id = :id AND status = 'draft'"
                ),
                {"id": release_id, "m": json.dumps(manifest)},
            ).rowcount
            if updated != 1:  # pragma: no cover - corrida entre validadores
                msg = "release alterado concorrentemente durante a validação"
                raise PublicationError(msg)
            self._event(conn, release_id, "draft", "validated")
        return self.get(release_id)

    def activate(self, release_id: str) -> Release:
        """``validated`` → ``active`` atomicamente. O anterior vira ``superseded``."""
        try:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        "SELECT scope, status FROM publication.release "
                        "WHERE release_id = :id FOR UPDATE"
                    ),
                    {"id": release_id},
                ).first()
                if row is None:
                    msg = f"release inexistente: {release_id}"
                    raise PublicationError(msg)
                scope, status = row
                if status != "validated":
                    msg = f"apenas releases validados podem ser ativados (atual: {status})"
                    raise PublicationError(msg)
                # Serializa ativações concorrentes do mesmo escopo.
                conn.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
                    {"k": f"odb.publication:{scope}"},
                )
                previous = conn.execute(
                    text(
                        "UPDATE publication.release SET status = 'superseded', "
                        "superseded_at = now() WHERE scope = :s AND status = 'active' "
                        "RETURNING release_id::text"
                    ),
                    {"s": scope},
                ).scalar()
                conn.execute(
                    text(
                        "UPDATE publication.release SET status = 'active', activated_at = now() "
                        "WHERE release_id = :id"
                    ),
                    {"id": release_id},
                )
                # Confirmação final dentro da transação: as versões ainda existem no log Delta?
                release = self._load(conn, "WHERE release_id = :id", {"id": release_id})
                assert release is not None  # noqa: S101 - travado acima
                problems = self._problems(release)
                if problems:
                    msg = "ativação abortada: " + "; ".join(problems)
                    raise PublicationError(msg)
                if previous is not None:
                    self._event(conn, previous, "active", "superseded", {"by": release_id})
                self._event(conn, release_id, "validated", "active", {"previous": previous})
        except PublicationError as exc:
            if "ativação abortada" in str(exc):
                self._fail(release_id, "validated", str(exc))
            raise
        except Exception as exc:
            self._fail(release_id, "validated", f"{type(exc).__name__}: {exc}")
            raise
        return self.get(release_id)
