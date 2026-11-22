"""Montagem dos componentes da API (injeção de dependências)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import Engine

from odb_api.config import ApiSettings
from odb_api.contas import ContasService
from odb_api.gold import GoldGateway
from odb_api.kpis import KpiService
from odb_api.metrics import MetricsService
from odb_api.release import ReleaseResolver
from odb_api.repository import CatalogRepository
from odb_catalog.access_metrics import MetricsReader, metrics_engine
from odb_catalog.db import make_engine
from odb_catalog.publication import PublicationError, PublicationService, Release
from odb_common.settings import Settings
from odb_common.storage import LakehouseLayout, Layer
from odb_ingestion.config import SourceCatalog, load_sources
from odb_query_engine import DuckDBConfig, DuckDBReadEngine, ReadEngine
from odb_semantics import load_panorama
from odb_semantics.portal import load_portal, load_short_labels


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
    # Métricas de acesso (ADR-0027); None sem o banco odb_metrics configurado.
    metrics: MetricsService | None = None
    # Bloco de contas públicas (ADR-0037); None desliga as rotas /contas (503).
    contas: ContasService | None = None
    closers: list[object] = field(default_factory=list)

    def close(self) -> None:
        """Libera conexões."""
        for item in self.closers:
            if isinstance(item, Engine):
                item.dispose()
            elif hasattr(item, "close"):
                item.close()


def provenance(sources: SourceCatalog) -> dict[str, tuple[str, str | None]]:
    """Dataset → (sigla da instituição, sistema): "SIDRA" para o conector do SIDRA."""
    out: dict[str, tuple[str, str | None]] = {}
    for dataset_id, dataset in sources.datasets.items():
        institution = sources.institutions[sources.source_institution[dataset.source]]
        connector = sources.sources[dataset.source].connector
        out[dataset_id] = (institution.acronym, "SIDRA" if connector == "sidra" else None)
        # Série de datasets (silver.series): a proveniência é a dos membros.
        series = dataset.silver.get("series")
        if series:
            out.setdefault(str(series), out[dataset_id])
    # Séries compostas (ADR-0022): a proveniência do membro mais recente.
    for series_id, ser in sources.series.items():
        out.setdefault(series_id, out[ser.members[-1]])
    return out


def table_links(sources: SourceCatalog) -> dict[str, str]:
    """Tabela de origem → link oficial, do ``reference_url`` de cada dataset configurado.

    No SIDRA a tabela é ``params.table`` (a mesma gravada em ``source_table_id``); nas
    demais fontes, o ``official_id``. O link nunca é montado à mão.
    """
    out: dict[str, str] = {}
    for dataset in sources.datasets.values():
        if not dataset.reference_url:
            continue
        table = str(dataset.params.get("table") or dataset.official_id)
        out.setdefault(table, dataset.reference_url)
    return out


_SERVABLE = ("validated", "active")


def contas_loader(
    publication: PublicationService, api: ApiSettings
) -> Callable[[], Release | None]:
    """Release das contas: o ativo do escopo ou, na homologação, o fixado por id."""
    if not api.contas_release_id:
        return lambda: publication.active(api.contas_scope)

    def pinned() -> Release | None:
        try:
            release = publication.get(api.contas_release_id)
        except PublicationError:
            return None
        if release.scope != api.contas_scope or release.status not in _SERVABLE:
            return None
        return release

    return pinned


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
    sources = load_sources(settings.sources_config_dir)
    metrics_pg = metrics_engine(settings, "reader")
    return ApiDeps(
        settings=api,
        resolver=ReleaseResolver(lambda: publication.active(api.scope), ttl_s=api.release_ttl_s),
        gold=gold,
        kpis=KpiService(
            gold,
            portal,
            page_max=api.page_max,
            panorama=panorama,
            provenance=provenance(sources),
            table_links=table_links(sources),
            labels=load_short_labels(Path(api.portal_config_dir) / "rotulos.toml"),
        ),
        catalog=CatalogRepository(pg),
        engine=duck,
        metrics=MetricsService(MetricsReader(metrics_pg)) if metrics_pg else None,
        contas=ContasService(
            gold, ReleaseResolver(contas_loader(publication, api), ttl_s=api.release_ttl_s)
        ),
        closers=[duck, pg, *([metrics_pg] if metrics_pg else [])],
    )
