"""Catálogo de fontes e datasets e registro de ingestões Bronze (Fase 2).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_ID = r"'^[a-z0-9][a-z0-9\-]{0,63}$'"


def upgrade() -> None:
    """Cria o schema catalog e as tabelas de ingestão em operations."""
    op.execute(
        f"""
        CREATE SCHEMA catalog;

        CREATE TABLE catalog.institution (
            institution_id text PRIMARY KEY CHECK (institution_id ~ {_ID}),
            name           text NOT NULL,
            acronym        text NOT NULL,
            url            text NOT NULL,
            updated_at     timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE catalog.license (
            license_id    text PRIMARY KEY CHECK (license_id ~ {_ID}),
            name          text NOT NULL,
            url           text,
            conditions    text NOT NULL,
            review_status text NOT NULL CHECK (review_status IN ('approved', 'requires_review')),
            notes         text,
            updated_at    timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE catalog.source (
            source_id         text PRIMARY KEY CHECK (source_id ~ {_ID}),
            institution_id    text NOT NULL REFERENCES catalog.institution (institution_id),
            name              text NOT NULL,
            connector_type    text NOT NULL,
            base_url          text NOT NULL,
            documentation_url text,
            updated_at        timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE catalog.dataset (
            dataset_id            text PRIMARY KEY CHECK (dataset_id ~ {_ID}),
            source_id             text NOT NULL REFERENCES catalog.source (source_id),
            official_id           text NOT NULL,
            title                 text NOT NULL,
            description           text NOT NULL,
            license_id            text NOT NULL REFERENCES catalog.license (license_id),
            access_classification text NOT NULL CHECK (access_classification IN (
                'public_authorized', 'public_conditional', 'requires_review',
                'restricted', 'forbidden')),
            periodicity           text NOT NULL,
            reference_url         text,
            enabled               boolean NOT NULL DEFAULT true,
            config                jsonb NOT NULL,
            config_sha256         char(64) NOT NULL,
            updated_at            timestamptz NOT NULL DEFAULT now()
        );

        -- Uma tentativa de ingestão de um dataset.
        CREATE TABLE operations.ingestion (
            ingestion_id uuid PRIMARY KEY,
            run_id       uuid REFERENCES operations.pipeline_run (run_id),
            dataset_id   text NOT NULL REFERENCES catalog.dataset (dataset_id),
            status       text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
            parameters   jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            plan         jsonb NOT NULL DEFAULT '[]'::jsonb,
            stats        jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            started_at   timestamptz NOT NULL DEFAULT now(),
            finished_at  timestamptz,
            error        text,
            CHECK ((status = 'running') = (finished_at IS NULL)),
            CHECK (status <> 'failed' OR error IS NOT NULL)
        );
        CREATE INDEX ingestion_dataset_started_idx
            ON operations.ingestion (dataset_id, started_at DESC);

        -- Cada artefato obtido (ou tentativa de obtenção) de uma ingestão.
        CREATE TABLE operations.bronze_artifact (
            artifact_id           uuid PRIMARY KEY,
            ingestion_id          uuid NOT NULL REFERENCES operations.ingestion (ingestion_id),
            dataset_id            text NOT NULL REFERENCES catalog.dataset (dataset_id),
            partition_key         text NOT NULL,
            source_url            text NOT NULL,
            retrieved_at          timestamptz NOT NULL,
            http_status           integer,
            content_type          text,
            file_size_bytes       bigint CHECK (file_size_bytes >= 0),
            checksum_sha256       char(64),
            storage_uri           text,
            reused_from           uuid REFERENCES operations.bronze_artifact (artifact_id),
            source_version        text,
            reference_period      text,
            license_id            text NOT NULL REFERENCES catalog.license (license_id),
            access_classification text NOT NULL,
            ingestion_status      text NOT NULL CHECK (ingestion_status IN (
                'stored', 'reused', 'not_modified', 'quarantined', 'failed')),
            validation            jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            response_headers      jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            error                 text,
            CHECK (ingestion_status NOT IN ('stored', 'reused', 'quarantined')
                   OR (checksum_sha256 IS NOT NULL AND storage_uri IS NOT NULL)),
            CHECK ((ingestion_status = 'reused') = (reused_from IS NOT NULL))
        );
        -- Os bytes de um conteúdo válido são gravados uma única vez (deduplicação global).
        CREATE UNIQUE INDEX bronze_artifact_stored_checksum_uq
            ON operations.bronze_artifact (checksum_sha256) WHERE ingestion_status = 'stored';
        CREATE INDEX bronze_artifact_dataset_idx
            ON operations.bronze_artifact (dataset_id, partition_key, retrieved_at DESC);
        CREATE INDEX bronze_artifact_ingestion_idx ON operations.bronze_artifact (ingestion_id);

        -- Último estado válido conhecido de cada partição (detecção de mudanças).
        CREATE TABLE operations.watermark (
            dataset_id      text NOT NULL REFERENCES catalog.dataset (dataset_id),
            partition_key   text NOT NULL,
            checksum_sha256 char(64),
            artifact_id     uuid REFERENCES operations.bronze_artifact (artifact_id),
            source_version  text,
            etag            text,
            last_modified   text,
            updated_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (dataset_id, partition_key)
        );
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_pipeline') THEN
                GRANT USAGE ON SCHEMA catalog TO odb_pipeline;
                GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA catalog TO odb_pipeline;
                GRANT SELECT, INSERT, UPDATE ON operations.ingestion, operations.bronze_artifact,
                    operations.watermark TO odb_pipeline;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odb_reader') THEN
                GRANT USAGE ON SCHEMA catalog TO odb_reader;
                GRANT SELECT ON ALL TABLES IN SCHEMA catalog TO odb_reader;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove as tabelas desta revisão."""
    op.execute(
        """
        DROP TABLE operations.watermark;
        DROP TABLE operations.bronze_artifact;
        DROP TABLE operations.ingestion;
        DROP SCHEMA catalog CASCADE;
        """
    )
