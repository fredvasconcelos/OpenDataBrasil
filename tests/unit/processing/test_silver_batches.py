"""Lotes de períodos da Silver SIDRA e junção das verificações."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from odb_processing.quality import CheckResult, CheckStatus
from odb_processing.silver import SilverInput, _period_batches, merge_checks


def _input(tmp: Path, key: str, size: int) -> SilverInput:
    path = tmp / f"{key}.json"
    path.write_bytes(b"x" * size)
    return SilverInput(
        partition_key=key,
        artifact_id=key,
        ingestion_id="i",
        storage_uri=path.as_uri(),
        checksum_sha256="c",
        source_url="u",
        retrieved_at=datetime.now(UTC),
        reference_period=None,
    )


def test_batches_keep_periods_together(tmp_path: Path) -> None:
    inputs = [
        _input(tmp_path, "n1n2n3n6-p2021", 40),
        _input(tmp_path, "n1n2n3n6-p2021-xc58", 40),  # mesmo período, outro conjunto
        _input(tmp_path, "n1n2n3n6-p2022", 50),
        _input(tmp_path, "n1n2n3n6-p2023", 200),  # maior que o limite: lote sozinho
    ]
    batches = _period_batches(inputs, 100)
    assert [[i.partition_key for i in b] for b in batches] == [
        ["n1n2n3n6-p2021", "n1n2n3n6-p2021-xc58"],
        ["n1n2n3n6-p2022"],
        ["n1n2n3n6-p2023"],
    ]


def test_merge_checks_keeps_worst_status() -> None:
    merged = merge_checks(
        [
            CheckResult("a", CheckStatus.PASS, "ok"),
            CheckResult("a", CheckStatus.WARN, "aviso no lote 2"),
            CheckResult("b", CheckStatus.PASS, "ok"),
        ]
    )
    by_id = {c.check_id: c for c in merged}
    assert by_id["a"].status is CheckStatus.WARN
    assert by_id["a"].details["lotes"] == 2
    assert by_id["b"].details == {}
