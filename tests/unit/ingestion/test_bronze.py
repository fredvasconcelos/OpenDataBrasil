import hashlib
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from odb_common.storage import LakehouseLayout
from odb_ingestion.bronze import BronzeIntegrityError, BronzeStore, sha256_file, snapshot_segment


@pytest.fixture
def store(tmp_path: Path) -> BronzeStore:
    return BronzeStore(LakehouseLayout((tmp_path / "lake").as_uri()))


def _temp(tmp_path: Path, content: bytes = b"dados") -> tuple[Path, str]:
    path = tmp_path / "staged.bin"
    path.write_bytes(content)
    return path, hashlib.sha256(content).hexdigest()


def test_snapshot_segment() -> None:
    started = datetime(2026, 11, 3, 18, 26, 47, tzinfo=UTC)
    assert (
        snapshot_segment(started, "1a2b3c4d-0000-0000-0000-000000000000")
        == "20261103t182647z-1a2b3c4d"
    )


def test_store_layout_read_only_and_verify(store: BronzeStore, tmp_path: Path) -> None:
    temp, sha = _temp(tmp_path)
    uri = store.store(
        temp,
        source_id="ibge-sidra",
        dataset_id="ibge-sidra-6579",
        snapshot="20261103t000000z-abcd1234",
        artifact_name="t6579-n6-p2025.json",
        expected_sha256=sha,
    )
    assert uri.endswith(
        "/bronze/ibge-sidra/ibge-sidra-6579/20261103t000000z-abcd1234/t6579-n6-p2025.json"
    )
    path = Path(uri.removeprefix("file://"))
    assert not path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    assert store.verify(uri, sha)
    assert not store.verify(uri, "0" * 64)
    assert sha256_file(path) == sha


def test_never_overwrites(store: BronzeStore, tmp_path: Path) -> None:
    temp, sha = _temp(tmp_path)
    args: dict[str, Any] = {
        "source_id": "s",
        "dataset_id": "d",
        "snapshot": "x",
        "artifact_name": "a.json",
    }
    store.store(temp, expected_sha256=sha, **args)
    with pytest.raises(FileExistsError):
        store.store(temp, expected_sha256=sha, **args)


def test_quarantine_and_integrity_error(store: BronzeStore, tmp_path: Path) -> None:
    temp, sha = _temp(tmp_path)
    uri = store.store(
        temp,
        source_id="s",
        dataset_id="d",
        snapshot="x",
        artifact_name="a.json",
        expected_sha256=sha,
        quarantine=True,
    )
    assert "/d/quarantine/x/a.json" in uri
    with pytest.raises(BronzeIntegrityError):
        store.store(
            temp,
            source_id="s",
            dataset_id="d",
            snapshot="y",
            artifact_name="a.json",
            expected_sha256="0" * 64,
        )
    assert not (store.bronze_root / "s" / "d" / "y" / "a.json").exists()


def test_staging_cleanup_and_remove_unregistered(store: BronzeStore, tmp_path: Path) -> None:
    staging = store.staging_dir("ing-1")
    (staging / "f").write_bytes(b"x")
    assert staging.parts[-3:] == ("tmp", "ingestion", "ing-1")
    store.cleanup_staging("ing-1")
    assert not (staging / "f").exists()
    temp, sha = _temp(tmp_path)
    uri = store.store(
        temp,
        source_id="s",
        dataset_id="d",
        snapshot="z",
        artifact_name="a.json",
        expected_sha256=sha,
    )
    store.remove_unregistered(uri)
    assert not Path(uri.removeprefix("file://")).exists()
    store.remove_unregistered(uri)  # idempotente
