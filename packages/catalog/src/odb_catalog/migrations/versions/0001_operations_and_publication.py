"""Schemas operations e publication (Fase 1).

Revision ID: 0001
Revises:
Create Date: 2026-11-03
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria execuções, releases, tabelas de release, eventos e privilégios."""
    op.execute(
        """
        CREATE SCHEMA operations;
        CREATE SCHEMA publication;

        -- Execuções de pipelines e comandos operacionais.
        CREATE TABLE operations.pipeline_run (
            run_id        uuid PRIMARY KEY,
            command       text        NOT NULL,
            status        text        NOT NULL
                CHECK (status IN ('running', 'succeeded', 'failed')),
            code_version  text        NOT NULL,
            parameters    jsonb       NOT NULL DEFAULT '{}'::jsonb,
            started_at    timestamptz NOT NULL DEFAULT now(),
            finished_at   timestamptz,
            error         text,
            CHECK ((status = 'running') = (finished_at IS NULL))
        );
        CREATE INDEX pipeline_run_started_idx ON operations.pipeline_run (started_at DESC);

        -- Release lógico: conjunto coerente de versões Delta de um escopo.
        CREATE TABLE publication.release (
            release_id     uuid PRIMARY KEY,
            scope          text        NOT NULL CHECK (scope ~ '^[a-z][a-z0-9_.-]{0,62}$'),
            status         text        NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'validated', 'active', 'superseded', 'failed')),
            code_version   text        NOT NULL,
            manifest       jsonb       NOT NULL DEFAULT '{}'::jsonb,
            created_by     text        NOT NULL,
            created_at     timestamptz NOT NULL DEFAULT now(),
            validated_at   timestamptz,
            activated_at   timestamptz,
            superseded_at  timestamptz,
            failure_reason text,
            CHECK (status <> 'active' OR activated_at IS NOT NULL),
            CHECK (status <> 'failed' OR failure_reason IS NOT NULL)
        );
        -- No máximo um release ativo por escopo.
        CREATE UNIQUE INDEX release_one_active_per_scope
            ON publication.release (scope) WHERE status = 'active';
        CREATE INDEX release_scope_created_idx ON publication.release (scope, created_at DESC);

        -- Versão Delta fixada de cada tabela incluída no release.
        CREATE TABLE publication.release_table (
            release_id       uuid   NOT NULL
                REFERENCES publication.release (release_id) ON DELETE RESTRICT,
            table_id         text   NOT NULL CHECK (table_id ~ '^[a-z][a-z0-9_.]{0,127}$'),
            storage_uri      text   NOT NULL,
            delta_version    bigint NOT NULL CHECK (delta_version >= 0),
            contract_version text   NOT NULL,
            quality_status   text   NOT NULL
                CHECK (quality_status IN ('passed', 'failed', 'not_run')),
            PRIMARY KEY (release_id, table_id)
        );

        -- Trilha de auditoria das transições de estado.
        CREATE TABLE publication.release_event (
            event_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id  uuid        NOT NULL REFERENCES publication.release (release_id),
            from_status text,
            to_status   text        NOT NULL,
            actor       text        NOT NULL,
            detail      jsonb       NOT NULL DEFAULT '{}'::jsonb,
            occurred_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX release_event_release_idx ON publication.release_event (release_id);
        """
    )
    # Privilégios condicionados à existência dos roles (criados pelo init do container).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_pipeline') THEN
                GRANT USAGE ON SCHEMA operations, publication TO odb_pipeline;
                GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA operations TO odb_pipeline;
                GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA publication TO odb_pipeline;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_reader') THEN
                GRANT USAGE ON SCHEMA publication TO odb_reader;
                GRANT SELECT ON publication.release, publication.release_table TO odb_reader;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove os schemas criados nesta revisão."""
    op.execute("DROP SCHEMA publication CASCADE; DROP SCHEMA operations CASCADE;")
