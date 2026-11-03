"""Registro de conectores disponíveis por tipo."""

from odb_ingestion.config import ConfigError, SourceCatalog
from odb_ingestion.connectors.http_file import HttpFileConnector
from odb_ingestion.connectors.sidra import SidraConnector
from odb_ingestion.contract import BaseConnector

CONNECTOR_TYPES: dict[str, type[BaseConnector]] = {
    SidraConnector.connector_type: SidraConnector,
    HttpFileConnector.connector_type: HttpFileConnector,
}


def build_connectors(catalog: SourceCatalog) -> dict[str, BaseConnector]:
    """Instancia um conector por fonte, validando os parâmetros de seus datasets."""
    connectors: dict[str, BaseConnector] = {}
    for source in catalog.sources.values():
        cls = CONNECTOR_TYPES.get(source.connector)
        if cls is None:
            msg = f"fonte {source.id}: tipo de conector desconhecido {source.connector!r}"
            raise ConfigError(msg)
        connectors[source.id] = cls(source, catalog.datasets_of(source.id))
    return connectors


__all__ = ["CONNECTOR_TYPES", "HttpFileConnector", "SidraConnector", "build_connectors"]
