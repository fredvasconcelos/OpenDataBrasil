import shutil
from collections import namedtuple
from pathlib import Path

import pytest

from odb_lakehouse.disk import DiskCapacityError, DiskLevel, disk_status, ensure_capacity
from odb_lakehouse.locking import InProcessLock, LockUnavailableError, lock_key

usage = namedtuple("usage", "total used free")


@pytest.mark.parametrize(
    ("used", "level"), [(10, DiskLevel.OK), (80, DiskLevel.WARN), (90, DiskLevel.BLOCK)]
)
def test_disk_levels(monkeypatch: pytest.MonkeyPatch, used: int, level: DiskLevel) -> None:
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: usage(100, used, 100 - used))
    assert disk_status("/", 80, 90).level is level


def test_disk_status_walks_to_existing_parent(tmp_path: Path) -> None:
    status = disk_status(tmp_path / "missing" / "deeper", 80, 90)
    assert status.path == str(tmp_path)
    assert status.total_bytes > 0


def test_ensure_capacity_raises_on_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: usage(100, 99, 1))
    with pytest.raises(DiskCapacityError, match=r"99\.0%"):
        ensure_capacity("/", 80, 90)
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: usage(0, 0, 0))
    assert disk_status("/", 80, 90).level is DiskLevel.BLOCK


def test_lock_key_stable_signed_and_normalized() -> None:
    key = lock_key("file:///lakehouse/gold/a")
    assert key == lock_key("file:///lakehouse/gold/a/")
    assert key != lock_key("file:///lakehouse/gold/b")
    assert -(2**63) <= key < 2**63


def test_in_process_lock_is_exclusive_and_released() -> None:
    lock = InProcessLock()
    with lock.hold("file:///x"):
        with pytest.raises(LockUnavailableError), lock.hold("file:///x"):
            pass
        with lock.hold("file:///y"):
            pass
    with lock.hold("file:///x"):
        pass
