"""Framework de ingestão da plataforma (Bronze)."""

from odb_ingestion.bronze import BronzeStore
from odb_ingestion.config import ConfigError, SourceCatalog, load_sources
from odb_ingestion.connectors import build_connectors
from odb_ingestion.contract import (
    BaseConnector,
    Capability,
    ExtractionPlan,
    ExtractionRequest,
    PartitionState,
    ValidationResult,
    Watermark,
)
from odb_ingestion.http import HttpClient, HttpError
from odb_ingestion.runner import (
    ArtifactRecord,
    Checkpoint,
    DeferredIngestionError,
    DuplicateContentError,
    IngestionRegistry,
    IngestionReport,
    IngestionRunner,
    StoredArtifact,
)

__all__ = [
    "ArtifactRecord",
    "BaseConnector",
    "BronzeStore",
    "Capability",
    "Checkpoint",
    "ConfigError",
    "DeferredIngestionError",
    "DuplicateContentError",
    "ExtractionPlan",
    "ExtractionRequest",
    "HttpClient",
    "HttpError",
    "IngestionRegistry",
    "IngestionReport",
    "IngestionRunner",
    "PartitionState",
    "SourceCatalog",
    "StoredArtifact",
    "ValidationResult",
    "Watermark",
    "build_connectors",
    "load_sources",
]
