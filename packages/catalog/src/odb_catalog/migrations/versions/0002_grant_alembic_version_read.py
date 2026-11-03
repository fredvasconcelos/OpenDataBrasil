"""Leitura de alembic_version pelos roles da aplicação.

Necessária para o `odb doctor` verificar a revisão aplicada usando o role do
próprio serviço (odb_pipeline/odb_reader) em vez do odb_owner.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Concede SELECT em public.alembic_version, se os roles existirem."""
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
            FOREACH r IN ARRAY ARRAY['odb_pipeline', 'odb_reader'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('GRANT SELECT ON public.alembic_version TO %I', r);
                END IF;
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Revoga o privilégio concedido."""
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
            FOREACH r IN ARRAY ARRAY['odb_pipeline', 'odb_reader'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('REVOKE SELECT ON public.alembic_version FROM %I', r);
                END IF;
            END LOOP;
        END
        $$;
        """
    )
