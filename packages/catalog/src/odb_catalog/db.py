"""Fábrica de engines SQLAlchemy para o catálogo."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from odb_common.settings import Settings


def make_engine(settings: Settings, *, pool_size: int = 5) -> Engine:
    """Engine com pool pequeno e ``application_name`` identificável no PostgreSQL."""
    return create_engine(
        settings.postgres_url(),
        pool_size=pool_size,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={"application_name": f"odb-{settings.env}"},
    )
