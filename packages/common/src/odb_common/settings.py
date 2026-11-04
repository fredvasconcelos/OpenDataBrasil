"""Configuração da plataforma.

Precedência, da maior para a menor:

1. argumentos explícitos (``load_settings(**overrides)``);
2. variáveis de ambiente com prefixo ``ODB_``;
3. arquivo ``<ODB_CONFIG_DIR>/<ODB_ENV>.toml`` (padrão: ``configs/environments``);
4. valores padrão definidos aqui.

Segredos (senhas) só são aceitos por variável de ambiente ou argumento. Nunca
devem ser colocados nos arquivos TOML versionados.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

Environment = Literal["dev", "test"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

DEFAULT_CONFIG_DIR = Path("configs/environments")


def config_file_path() -> Path:
    """Retorna o caminho do TOML do ambiente selecionado por ``ODB_ENV``."""
    env = os.environ.get("ODB_ENV", "dev")
    config_dir = Path(os.environ.get("ODB_CONFIG_DIR", str(DEFAULT_CONFIG_DIR)))
    return config_dir / f"{env}.toml"


class Settings(BaseSettings):
    """Configuração imutável de um processo da plataforma."""

    model_config = SettingsConfigDict(
        env_prefix="ODB_",
        extra="ignore",
        frozen=True,
    )

    env: Environment = "dev"
    log_level: LogLevel = "INFO"
    # Commit do código em execução (injetado no build da imagem).
    code_version: str = "unknown"
    # Configurações versionadas das fontes de dados (um TOML por fonte).
    sources_config_dir: str = "configs/sources"
    # Catálogo semântico (indicadores, classificações e fatos; um TOML por escopo).
    indicators_config_dir: str = "configs/indicators"

    # Lakehouse
    lakehouse_root_uri: str = "file:///lakehouse"
    disk_warn_percent: int = Field(default=80, ge=1, le=99)
    disk_block_percent: int = Field(default=90, ge=1, le=100)

    # PostgreSQL: a identidade (role) depende do serviço que executa o processo.
    pg_host: str = "localhost"
    pg_port: int = Field(default=5432, ge=1, le=65535)
    pg_database: str = "odb"
    pg_user: str = "odb_reader"
    pg_password: SecretStr = SecretStr("")
    pg_connect_timeout_s: int = Field(default=5, ge=1)

    # DuckDB (motor de consulta, somente leitura)
    duckdb_memory_limit: str = "4GB"
    duckdb_threads: int = Field(default=4, ge=1)
    duckdb_temp_directory: str = "/lakehouse/tmp/duckdb"
    duckdb_max_temp_directory_size: str = "20GB"
    duckdb_query_timeout_s: float = Field(default=30.0, gt=0)
    duckdb_max_rows: int = Field(default=100_000, ge=1)
    duckdb_max_concurrent_queries: int = Field(default=4, ge=1)
    # Diretório com extensões pré-instaladas (imagem Docker). None = padrão do DuckDB.
    duckdb_extension_directory: str | None = None

    @model_validator(mode="after")
    def _check_disk_thresholds(self) -> Settings:
        if self.disk_warn_percent >= self.disk_block_percent:
            msg = "disk_warn_percent deve ser menor que disk_block_percent"
            raise ValueError(msg)
        return self

    def postgres_url(self, driver: str = "postgresql+psycopg") -> str:
        """URL SQLAlchemy. A senha é incluída, então nunca registre o retorno em log."""
        password = quote(self.pg_password.get_secret_value(), safe="")
        user = quote(self.pg_user, safe="")
        return (
            f"{driver}://{user}:{password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"
            f"?connect_timeout={self.pg_connect_timeout_s}"
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define a precedência: argumentos > ambiente > TOML do ambiente > padrões."""
        toml_source = TomlConfigSettingsSource(settings_cls, toml_file=config_file_path())
        return (init_settings, env_settings, toml_source)


def load_settings(**overrides: object) -> Settings:
    """Carrega a configuração aplicando a precedência documentada no módulo."""
    return Settings(**overrides)  # type: ignore[arg-type]
