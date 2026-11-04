"""Registro Gold em memória e ambiente completo Bronze → Silver → Gold para testes."""

from collections.abc import Sequence
from pathlib import Path

from odb_common.storage import LakehouseLayout
from odb_ingestion import BronzeStore, HttpClient, IngestionRunner, build_connectors, load_sources
from odb_ingestion.contract import BaseConnector
from odb_lakehouse import DeltaWriter, InProcessLock
from odb_modeling.builder import GoldBuild, GoldBuilder, PreviousGoldBuild
from odb_processing.quality import CheckResult
from odb_processing.silver import PreviousRun, SilverBuilder
from odb_semantics import SemanticCatalog, load_scope
from tests.ingestion_support import TEST_SOURCES, FakeSources, InMemoryRegistry
from tests.silver_support import InMemorySilverRegistry

REPO_INDICATORS = Path(__file__).resolve().parents[1] / "configs" / "indicators"
SIDRA_DATASETS = [
    "ibge-sidra-6579",
    "ibge-sidra-4714",
    "ibge-sidra-9605",
    "ibge-sidra-9718",
    "ibge-sidra-9578",
    "ibge-sidra-9971",
    "ibge-sidra-9970",
    "ibge-sidra-9723",
]
ALL_DATASETS = ["ibge-dtb", *SIDRA_DATASETS]


class InMemoryGoldRegistry:
    def __init__(self, silver: InMemorySilverRegistry) -> None:
        self.silver = silver
        self.builds: list[GoldBuild] = []
        self.checks: dict[str, list[CheckResult]] = {}

    def silver_success(self, dataset_id: str) -> PreviousRun | None:
        return self.silver.last_success(dataset_id)

    def last_success(self, scope: str) -> PreviousGoldBuild | None:
        for b in reversed(self.builds):
            if b.scope == scope and b.status in ("succeeded", "skipped"):
                return PreviousGoldBuild(b.build_id, b.input_fingerprint, dict(b.tables))
        return None

    def start_build(self, build: GoldBuild, *, pipeline_run_id: str | None) -> None:
        self.builds.append(build)

    def finish_build(self, build: GoldBuild) -> None:
        assert build.status != "running"

    def record_checks(self, build_id: str, scope: str, results: Sequence[CheckResult]) -> None:
        self.checks[build_id] = list(results)


class GoldEnv:
    """Fontes simuladas (fixtures reais) → Bronze → Silver → Gold em diretório temporário."""

    def __init__(self, tmp_path: Path, catalog: SemanticCatalog | None = None) -> None:
        self.sources = load_sources(TEST_SOURCES)
        self.layout = LakehouseLayout((tmp_path / "lake").as_uri())
        self.fake = FakeSources()
        self.ingestion = InMemoryRegistry()

        def factory(connector: BaseConnector) -> HttpClient:
            return HttpClient(
                connector.source.http, transport=self.fake.transport(), sleep=lambda _s: None
            )

        self.runner = IngestionRunner(
            self.sources,
            build_connectors(self.sources),
            BronzeStore(self.layout),
            self.ingestion,
            factory,
        )
        self.writer = DeltaWriter(self.layout, InProcessLock())
        self.silver_registry = InMemorySilverRegistry(self.ingestion)
        self.silver = SilverBuilder(
            self.sources, self.layout, self.writer, self.silver_registry, code_version="test"
        )
        self.catalog = catalog or load_scope(REPO_INDICATORS, "demografia")
        self.registry = InMemoryGoldRegistry(self.silver_registry)
        self.gold = GoldBuilder(
            self.sources, self.catalog, self.layout, self.writer, self.registry, code_version="test"
        )

    def prepare(self, datasets: Sequence[str] = tuple(ALL_DATASETS)) -> None:
        for d in datasets:
            run = self.runner.run(d)
            assert run.status == "succeeded", run
        runs = self.silver.build_many(list(datasets))
        assert all(r.status == "succeeded" for r in runs), [(r.dataset_id, r.error) for r in runs]
