import shutil
from collections import namedtuple
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from odb_common.storage import LakehouseLayout, Layer
from odb_lakehouse.disk import DiskCapacityError
from odb_lakehouse.locking import InProcessLock, LockUnavailableError
from odb_lakehouse.protocol import ProtocolViolationError
from odb_lakehouse.tables import DeltaReader, DeltaWriter, TableWriteError
from tests.contracts.delta_interop.conftest import make_frame


@pytest.fixture
def layout(tmp_path: Path) -> LakehouseLayout:
    return LakehouseLayout(tmp_path.as_uri())


@pytest.fixture
def lock() -> InProcessLock:
    return InProcessLock()


@pytest.fixture
def writer(layout: LakehouseLayout, lock: InProcessLock) -> DeltaWriter:
    return DeltaWriter(layout, lock)


@pytest.fixture
def uri(layout: LakehouseLayout) -> str:
    return layout.table_uri(Layer.GOLD, "demo", "fact_obs")


reader = DeltaReader()


def test_write_create_append_and_lineage(writer: DeltaWriter, uri: str) -> None:
    first = writer.write(uri, make_frame([1, 2]), run_id="run-a")
    assert first.version == 0
    assert first.operation == "write:error"
    second = writer.write(uri, make_frame([3]), run_id="run-b")
    assert second.version == 1
    assert second.metrics["num_added_rows"] == 1
    history = reader.history(uri)
    assert [h["odb.run_id"] for h in history] == ["run-b", "run-a"]
    assert reader.current_version(uri) == 1
    assert reader.scan(uri, 0).select(pl.len()).collect().item() == 2


def test_overwrite_keeps_previous_version_readable(writer: DeltaWriter, uri: str) -> None:
    writer.write(uri, make_frame([1, 2]), run_id="r")
    result = writer.write(uri, make_frame([9]), run_id="r", mode="overwrite")
    assert result.version == 1
    assert reader.scan(uri, 0).select(pl.len()).collect().item() == 2
    assert reader.scan(uri, 1).select(pl.len()).collect().item() == 1


def test_partitioning_fixed_at_creation(writer: DeltaWriter, uri: str) -> None:
    writer.write(uri, make_frame([1]), run_id="r", partition_by=["uf"])
    writer.write(uri, make_frame([2]), run_id="r", partition_by=["uf"])
    with pytest.raises(TableWriteError, match="particionamento"):
        writer.write(uri, make_frame([3]), run_id="r", partition_by=["obs_id"])


def test_schema_evolution_opt_in(writer: DeltaWriter, uri: str) -> None:
    writer.write(uri, make_frame([1]), run_id="r")
    evolved = make_frame([2]).with_columns(pl.lit("n").alias("note"))
    with pytest.raises(Exception, match=r"(?i)schema"):
        writer.write(uri, evolved, run_id="r")
    assert reader.current_version(uri) == 0
    assert writer.write(uri, evolved, run_id="r", evolve_schema=True).version == 1


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("bronze", "não aceita tabelas Delta"),
        ("outside", "fora do lakehouse"),
    ],
)
def test_rejects_non_writable_targets(
    writer: DeltaWriter, layout: LakehouseLayout, target: str, message: str
) -> None:
    uri = (
        layout.table_uri(Layer.BRONZE, "x")
        if target == "bronze"
        else "file:///somewhere/else/table"
    )
    with pytest.raises(TableWriteError, match=message):
        writer.write(uri, make_frame([1]), run_id="r")


def test_rejects_bad_columns_and_types(writer: DeltaWriter, uri: str) -> None:
    with pytest.raises(TableWriteError, match="colunas"):
        writer.write(uri, pl.DataFrame({"Bad Name": [1]}), run_id="r")
    with pytest.raises(ProtocolViolationError):
        writer.write(uri, pl.DataFrame({"n": pl.Series([1], dtype=pl.UInt64)}), run_id="r")
    with pytest.raises(TableWriteError, match="partição"):
        writer.write(uri, make_frame([1]), run_id="r", partition_by=["Bad"])


def test_lock_blocks_concurrent_writer(writer: DeltaWriter, lock: InProcessLock, uri: str) -> None:
    writer.write(uri, make_frame([1]), run_id="r")
    with lock.hold(uri), pytest.raises(LockUnavailableError):
        writer.write(uri, make_frame([2]), run_id="r")
    assert reader.current_version(uri) == 0
    assert writer.write(uri, make_frame([2]), run_id="r").version == 1  # lock liberado


def test_disk_block_prevents_write(
    writer: DeltaWriter, uri: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: usage(100, 95, 5))
    with pytest.raises(DiskCapacityError):
        writer.write(uri, make_frame([1]), run_id="r")
    assert not reader.has_version(uri, 0)


def test_merge_upsert(writer: DeltaWriter, uri: str) -> None:
    writer.write(uri, make_frame([1, 2]), run_id="r")
    result = writer.merge(uri, make_frame([2, 3], value="5.0000"), keys=["obs_id"], run_id="m")
    assert result.version == 1
    assert result.operation == "merge"
    assert result.metrics["num_target_rows_updated"] == 1
    rows = reader.scan(uri, 1).sort("obs_id").select("obs_id", "value").collect().rows()
    assert rows == [(1, Decimal("1.0000")), (2, Decimal("5.0000")), (3, Decimal("5.0000"))]


def test_merge_validations(writer: DeltaWriter, uri: str) -> None:
    with pytest.raises(TableWriteError, match="tabela existente"):
        writer.merge(uri, make_frame([1]), keys=["obs_id"], run_id="r")
    writer.write(uri, make_frame([1]), run_id="r")
    with pytest.raises(TableWriteError, match="ao menos uma"):
        writer.merge(uri, make_frame([1]), keys=[], run_id="r")
    with pytest.raises(TableWriteError, match="ausentes"):
        writer.merge(uri, make_frame([1]), keys=["nope"], run_id="r")
    with pytest.raises(TableWriteError, match="duplicadas"):
        writer.merge(uri, make_frame([1, 1]), keys=["obs_id"], run_id="r")
    nulls = make_frame([1]).with_columns(pl.lit(None, dtype=pl.Int64).alias("obs_id"))
    with pytest.raises(TableWriteError, match="nulos"):
        writer.merge(uri, nulls, keys=["obs_id"], run_id="r")
    with pytest.raises(TableWriteError, match="diferem"):
        writer.merge(uri, make_frame([1]).drop("ratio"), keys=["obs_id"], run_id="r")
    assert reader.current_version(uri) == 0


def test_reader_version_checks(writer: DeltaWriter, uri: str, tmp_path: Path) -> None:
    assert not reader.has_version(uri, 0)
    writer.write(uri, make_frame([1]), run_id="r")
    assert reader.has_version(uri, 0)
    assert not reader.has_version(uri, 1)
    assert not reader.has_version(uri, -1)
    with pytest.raises(ValueError, match="versão inválida"):
        reader.scan(uri, -1)


def test_replace_where_swaps_only_matching_rows(writer: DeltaWriter, uri: str) -> None:
    writer.write(uri, make_frame([1, 2], uf="SP"), run_id="r", partition_by=["uf"])
    writer.write(uri, make_frame([3], uf="RJ"), run_id="r")
    result = writer.write(
        uri, make_frame([9], uf="SP"), run_id="x", mode="overwrite", replace_where={"uf": "SP"}
    )
    assert result.operation == "write:replace_where"
    rows = reader.scan(uri, result.version).sort("obs_id").select("obs_id", "uf").collect().rows()
    assert rows == [(3, "RJ"), (9, "SP")]  # linhas SP antigas removidas, RJ intacta
    assert reader.scan(uri, 1).select(pl.len()).collect().item() == 3  # versão anterior preservada


def test_replace_where_creates_table_and_validates(writer: DeltaWriter, uri: str) -> None:
    created = writer.write(
        uri, make_frame([1], uf="SP"), run_id="r", mode="overwrite", replace_where={"uf": "SP"}
    )
    assert created.version == 0
    with pytest.raises(TableWriteError, match="não satisfazem"):
        writer.write(
            uri, make_frame([2], uf="RJ"), run_id="r", mode="overwrite", replace_where={"uf": "SP"}
        )
    with pytest.raises(TableWriteError, match="mode='overwrite'"):
        writer.write(uri, make_frame([2]), run_id="r", replace_where={"uf": "SP"})
    with pytest.raises(TableWriteError, match="ausente"):
        writer.write(
            uri, make_frame([2]), run_id="r", mode="overwrite", replace_where={"nope": "x"}
        )
    with pytest.raises(TableWriteError, match="ao menos uma"):
        writer.write(uri, make_frame([2]), run_id="r", mode="overwrite", replace_where={})
    assert reader.current_version(uri) == 0
