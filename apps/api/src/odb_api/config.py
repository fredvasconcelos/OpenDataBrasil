"""Configuração da API.

As conexões (PostgreSQL com o papel ``odb_reader``, lakehouse e limites do
DuckDB) vêm de ``odb_common.Settings``. Aqui ficam só os parâmetros do serviço
HTTP, com o prefixo ``ODB_API_``.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Parâmetros do serviço HTTP."""

    model_config = SettingsConfigDict(env_prefix="ODB_API_", extra="ignore", frozen=True)

    scope: str = "demografia"
    portal_config_dir: str = "configs/portal"
    # Taxonomia do panorama (ADR-0010). Vazio: navegação só com os KPIs do portal.
    panorama_path: str = "configs/catalog/panorama.toml"
    # Origens do portal autorizadas (CORS restritivo, §18.5).
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    # Por quanto tempo o release ativo lido do PostgreSQL é reaproveitado.
    release_ttl_s: float = Field(default=5.0, ge=0)
    page_max: int = Field(default=1000, ge=1, le=10_000)
    # Teto padrão da exportação síncrona. Só os dois KPIs LSPA têm 200 mil
    # (decisão de 18/11/2026); o motor tem orçamento próprio para exportações.
    export_max_rows: int = Field(default=100_000, ge=1)
    # Limite simples por IP; 0 desliga. Cache e limites finos ficam para a Fase 7.
    rate_limit_per_minute: int = Field(default=600, ge=0)
    # Redes (CIDR) dos proxies cujo X-Forwarded-For é aceito para identificar o cliente.
    # Na Vitrine, a rede interna do portal; vazio: só o IP da conexão (cada proxy vira
    # um único cliente e o limite passaria a valer para o site inteiro).
    trusted_proxies: tuple[str, ...] = ()
    # Cache de respostas por release, por processo (MiB); 0 desliga. Ligado na Vitrine.
    response_cache_mb: int = Field(default=0, ge=0, le=4096)
    geometry_cache_size: int = Field(default=8, ge=1)
