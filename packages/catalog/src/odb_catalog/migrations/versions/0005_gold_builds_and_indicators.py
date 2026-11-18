"""Construções Gold, resultados de qualidade da Gold e catálogo de indicadores (Fase 4).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-04
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria operations.gold_build, quality.gold_check_result e catalog.indicator."""
    op.execute(
        """
        CREATE TABLE operations.gold_build (
            build_id          uuid PRIMARY KEY,
            pipeline_run_id   uuid REFERENCES operations.pipeline_run (run_id),
            scope             text NOT NULL CHECK (scope ~ '^[a-z][a-z0-9_.-]{0,62}$'),
            config_version    text NOT NULL,
            code_version      text NOT NULL,
            input_fingerprint char(64) NOT NULL,
            inputs            jsonb NOT NULL DEFAULT '{}'::jsonb,
            status            text NOT NULL
                CHECK (status IN ('running', 'succeeded', 'skipped', 'failed')),
            -- {table_id: {storage_uri, delta_version, contract_version, rows}}
            tables            jsonb NOT NULL DEFAULT '{}'::jsonb,
            release_id        uuid REFERENCES publication.release (release_id),
            stats             jsonb NOT NULL DEFAULT '{}'::jsonb,
            started_at        timestamptz NOT NULL DEFAULT now(),
            finished_at       timestamptz,
            error             text,
            CHECK ((status = 'running') = (finished_at IS NULL)),
            CHECK (status <> 'failed' OR error IS NOT NULL),
            CHECK (status NOT IN ('succeeded', 'skipped') OR tables <> '{}'::jsonb)
        );
        CREATE INDEX gold_build_scope_idx ON operations.gold_build (scope, started_at DESC);

        CREATE TABLE quality.gold_check_result (
            result_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            build_id    uuid NOT NULL REFERENCES operations.gold_build (build_id),
            scope       text NOT NULL,
            check_id    text NOT NULL,
            status      text NOT NULL CHECK (status IN ('pass', 'warn', 'fail')),
            message     text NOT NULL,
            observed    jsonb,
            expected    jsonb,
            details     jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at  timestamptz NOT NULL DEFAULT now(),
            UNIQUE (build_id, check_id)
        );
        CREATE INDEX gold_check_result_scope_idx
            ON quality.gold_check_result (scope, created_at DESC);

        -- Definição semântica dos indicadores (metadados; os valores ficam na Gold).
        CREATE TABLE catalog.indicator (
            indicator_id       text PRIMARY KEY CHECK (indicator_id ~ '^[a-z][a-z0-9_]{0,63}$'),
            scope              text NOT NULL,
            name               text NOT NULL,
            description        text NOT NULL,
            dataset_id         text NOT NULL REFERENCES catalog.dataset (dataset_id),
            source_variable_id text NOT NULL,
            unit               text NOT NULL,
            additivity         text NOT NULL CHECK (additivity IN ('additive', 'non_additive')),
            concept            text NOT NULL,
            fact_table         text NOT NULL,
            theme_path         text[] NOT NULL,
            classification_ids text[] NOT NULL DEFAULT '{}',
            available_levels   text[] NOT NULL DEFAULT '{}',
            periods            text[] NOT NULL DEFAULT '{}',
            caveats            text[] NOT NULL DEFAULT '{}',
            incompatible_with  jsonb NOT NULL DEFAULT '[]'::jsonb,
            config_version     text NOT NULL,
            last_build_id      uuid REFERENCES operations.gold_build (build_id),
            updated_at         timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX indicator_scope_idx ON catalog.indicator (scope);
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_pipeline') THEN
                GRANT SELECT, INSERT, UPDATE ON operations.gold_build TO odb_pipeline;
                GRANT SELECT, INSERT ON quality.gold_check_result TO odb_pipeline;
                GRANT SELECT, INSERT, UPDATE ON catalog.indicator TO odb_pipeline;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_reader') THEN
                GRANT SELECT ON quality.gold_check_result, catalog.indicator TO odb_reader;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove as tabelas desta revisão."""
    op.execute(
        "DROP TABLE catalog.indicator; DROP TABLE quality.gold_check_result; "
        "DROP TABLE operations.gold_build;"
    )
