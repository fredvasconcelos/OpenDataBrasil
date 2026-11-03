from pathlib import PurePosixPath

import pytest

from odb_common.storage import LakehouseLayout, Layer, StorageError, uri_to_local_path


def test_table_uri_and_layer_roundtrip() -> None:
    layout = LakehouseLayout("file:///lakehouse/")
    uri = layout.table_uri(Layer.GOLD, "demography", "fact_population")
    assert uri == "file:///lakehouse/gold/demography/fact_population"
    assert layout.layer_of(uri) is Layer.GOLD
    assert uri_to_local_path(uri) == PurePosixPath("/lakehouse/gold/demography/fact_population")


@pytest.mark.parametrize("segment", ["..", "a/b", "Upper", "", ".hidden", "a b"])
def test_invalid_segments_rejected(segment: str) -> None:
    with pytest.raises(StorageError):
        LakehouseLayout("file:///lakehouse").table_uri(Layer.SILVER, segment)


@pytest.mark.parametrize(
    "root", ["s3://bucket/x", "file://remote-host/x", "file:///a/../b", "relative/path"]
)
def test_invalid_roots_rejected(root: str) -> None:
    with pytest.raises(StorageError):
        LakehouseLayout(root)


def test_requires_segment_and_known_layer() -> None:
    layout = LakehouseLayout("file:///lakehouse")
    with pytest.raises(StorageError):
        layout.table_uri(Layer.GOLD)
    with pytest.raises(StorageError):
        layout.layer_of("file:///other/gold/x")
    with pytest.raises(StorageError):
        layout.layer_of("file:///lakehouse/platinum/x")
    with pytest.raises(StorageError):
        uri_to_local_path("s3://bucket/key")
