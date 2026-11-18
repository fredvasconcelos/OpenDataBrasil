"""Registro Silver em memória ligado ao ``InMemoryRegistry`` de ingestão."""

from collections.abc import Sequence

from odb_processing.quality import CheckResult
from odb_processing.silver import PreviousRun, SilverInput, SilverRun
from tests.ingestion_support import InMemoryRegistry


class InMemorySilverRegistry:
    def __init__(self, ingestion: InMemoryRegistry) -> None:
        self.ingestion = ingestion
        self.runs: list[SilverRun] = []
        self.checks: dict[str, list[CheckResult]] = {}

    def current_inputs(self, dataset_id: str) -> list[SilverInput]:
        by_id = {a.artifact_id: a for a in self.ingestion.artifacts}
        inputs = []
        for key, artifact_id in self.ingestion.watermark_artifacts.get(dataset_id, {}).items():
            record = by_id[artifact_id]
            src = by_id[record.reused_from] if record.reused_from else record
            assert src.storage_uri
            assert src.checksum_sha256
            inputs.append(
                SilverInput(
                    partition_key=key,
                    artifact_id=src.artifact_id,
                    ingestion_id=src.ingestion_id,
                    storage_uri=src.storage_uri,
                    checksum_sha256=src.checksum_sha256,
                    source_url=src.source_url,
                    retrieved_at=src.retrieved_at,
                    reference_period=src.reference_period,
                )
            )
        return inputs

    def last_success(self, dataset_id: str) -> PreviousRun | None:
        for run in reversed(self.runs):
            if run.dataset_id == dataset_id and run.status in ("succeeded", "skipped"):
                return PreviousRun(
                    run.run_id, run.input_fingerprint, run.target_uri, run.delta_version
                )
        return None

    def start_run(
        self, run: SilverRun, *, pipeline_run_id: str | None, inputs: Sequence[SilverInput]
    ) -> None:
        self.runs.append(run)

    def finish_run(self, run: SilverRun) -> None:
        assert run.status != "running"

    def record_checks(self, run_id: str, dataset_id: str, results: Sequence[CheckResult]) -> None:
        self.checks[run_id] = list(results)
