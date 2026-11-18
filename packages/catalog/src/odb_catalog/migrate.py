"""Execução programática das migrações Alembic (sem alembic.ini)."""

from __future__ import annotations

from importlib.resources import files

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text


def alembic_config(url: str) -> Config:
    """Configuração Alembic apontando para as migrações empacotadas."""
    config = Config()
    config.set_main_option("script_location", str(files("odb_catalog") / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def upgrade(url: str, revision: str = "head") -> None:
    """Aplica migrações até ``revision``."""
    command.upgrade(alembic_config(url), revision)


def downgrade(url: str, revision: str) -> None:
    """Reverte migrações até ``revision`` (uso em desenvolvimento e testes)."""
    command.downgrade(alembic_config(url), revision)


def head_revision() -> str:
    """Revisão mais recente disponível no pacote."""
    head = ScriptDirectory.from_config(alembic_config("postgresql://unused")).get_current_head()
    if head is None:  # pragma: no cover - sempre há ao menos uma revisão
        msg = "nenhuma revisão de migração encontrada"
        raise RuntimeError(msg)
    return head


def current_revision(engine: Engine) -> str | None:
    """Revisão aplicada no banco, ou None se o banco não tiver migrações."""
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
        if exists is None:
            return None
        value = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        return str(value) if value is not None else None
