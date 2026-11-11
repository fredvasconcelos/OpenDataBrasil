"""Montagem dos componentes da API (injeção de dependências)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Engine

from odb_api.config import ApiSettings
from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService
from odb_api.portal import load_portal
from odb_api.release import ReleaseResolver
from odb_api.repository import CatalogRepository
from odb_catalog.db import make_engine
from odb_catalog.publication import PublicationService
from odb_common.settings import Settings
from odb_common.storage import LakehouseLayout, Layer
from odb_query_engine import DuckDBConfig, DuckDBReadEngine, ReadEngine
from odb_semantics import load_panorama


class _NoVerifier:
    """A API só lê releases; validar versões é papel do pipeline."""

    def has_version(self, table_uri: str, version: int) -> bool:
        msg = "a API não valida releases"
        raise NotImplementedError(msg)


@dataclass
class ApiDeps:
    """Componentes compartilhados pelas requisições."""

    settings: ApiSettings
    resolver: ReleaseResolver
    gold: GoldGateway
    kpis: KpiService
    catalog: CatalogRepository
    engine: ReadEngine
    closers: list[object] = field(default_factory=list)

    def close(self) -> None:
        """Libera conexões."""
        for item in self.closers:
            if isinstance(item, Engine):
                item.dispose()
            elif hasattr(item, "close"):
                item.close()


def build_deps(settings: Settings | None = None, api: ApiSettings | None = None) -> ApiDeps:
    """Componentes reais: PostgreSQL (``odb_reader``) e DuckDB restrito à Gold."""
    settings = settings or Settings()
    api = api or ApiSettings()
    pg = make_engine(settings, pool_size=5)
    publication = PublicationService(pg, _NoVerifier(), actor="api")
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    duck = DuckDBReadEngine(DuckDBConfig.from_settings(settings), [layout.layer_uri(Layer.GOLD)])
    gold = GoldGateway(duck, geometry_cache_size=api.geometry_cache_size)
    portal = load_portal(api.portal_config_dir, api.scope)
    panorama = load_panorama(api.panorama_path) if api.panorama_path else None
    return ApiDeps(
        settings=api,
        resolver=ReleaseResolver(lambda: publication.active(api.scope), ttl_s=api.release_ttl_s),
        gold=gold,
        kpis=KpiService(gold, portal, page_max=api.page_max, panorama=panorama),
        catalog=CatalogRepository(pg),
        engine=duck,
        closers=[duck, pg],
    )
