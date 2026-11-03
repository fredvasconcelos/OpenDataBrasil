"""Ambiente Alembic. A URL vem de ``odb_catalog.migrate``, nunca de alembic.ini."""

from alembic import context
from sqlalchemy import create_engine

config = context.config
url = config.get_main_option("sqlalchemy.url")
if not url:  # pragma: no cover - configurado por odb_catalog.migrate
    msg = "sqlalchemy.url não configurada; use `odb db upgrade`"
    raise RuntimeError(msg)

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, transaction_per_migration=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
