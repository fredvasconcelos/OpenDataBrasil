"""Execuções de transformação (Silver) e resultados de qualidade (Fase 3).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria operations.transformation_run e quality.check_result."""
    op.execute(
        """
        CREATE TABLE operations.transformation_run (
            run_id            uuid PRIMARY KEY,
            pipeline_run_id   uuid REFERENCES operations.pipeline_run (run_id),
            dataset_id        text NOT NULL REFERENCES catalog.dataset (dataset_id),
            layer             text NOT NULL CHECK (layer IN ('silver', 'gold')),
            target_uri        text NOT NULL,
            contract          text NOT NULL,
            contract_version  text NOT NULL,
            code_version      text NOT NULL,
            input_fingerprint char(64) NOT NULL,
            inputs            jsonb NOT NULL DEFAULT '[]'::jsonb,
            status            text NOT NULL
                CHECK (status IN ('running', 'succeeded', 'skipped', 'failed')),
            delta_version     bigint CHECK (delta_version >= 0),
            stats             jsonb NOT NULL DEFAULT '{}'::jsonb,
            started_at        timestamptz NOT NULL DEFAULT now(),
            finished_at       timestamptz,
            error             text,
            CHECK ((status = 'running') = (finished_at IS NULL)),
            CHECK (status <> 'failed' OR error IS NOT NULL),
            CHECK (status NOT IN ('succeeded', 'skipped') OR delta_version IS NOT NULL)
        );
        CREATE INDEX transformation_run_dataset_idx
            ON operations.transformation_run (dataset_id, layer, started_at DESC);

        CREATE SCHEMA quality;
        CREATE TABLE quality.check_result (
            result_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            run_id      uuid NOT NULL REFERENCES operations.transformation_run (run_id),
            dataset_id  text NOT NULL REFERENCES catalog.dataset (dataset_id),
            check_id    text NOT NULL,
            status      text NOT NULL CHECK (status IN ('pass', 'warn', 'fail')),
            message     text NOT NULL,
            observed    jsonb,
            expected    jsonb,
            details     jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at  timestamptz NOT NULL DEFAULT now(),
            UNIQUE (run_id, check_id)
        );
        CREATE INDEX check_result_dataset_idx ON quality.check_result (dataset_id, created_at DESC);
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_pipeline') THEN
                GRANT SELECT, INSERT, UPDATE ON operations.transformation_run TO odb_pipeline;
                GRANT USAGE ON SCHEMA quality TO odb_pipeline;
                GRANT SELECT, INSERT ON quality.check_result TO odb_pipeline;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_reader') THEN
                GRANT USAGE ON SCHEMA quality TO odb_reader;
                GRANT SELECT ON quality.check_result TO odb_reader;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove as tabelas desta revisão."""
    op.execute("DROP SCHEMA quality CASCADE; DROP TABLE operations.transformation_run;")
