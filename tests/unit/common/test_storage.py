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


def test_object_uri_and_filename_rules() -> None:
    layout = LakehouseLayout("file:///lakehouse")
    uri = layout.object_uri(Layer.BRONZE, "ibge-sidra", "ds", filename="p2025.json")
    assert uri == "file:///lakehouse/bronze/ibge-sidra/ds/p2025.json"
    assert layout.object_uri(Layer.BRONZE, "x", filename="dtb.tar.gz").endswith("/dtb.tar.gz")
    for bad in ["../x.json", "a/b.json", "UPPER.json", "x.json.gz.bak", ".hidden", "x."]:
        with pytest.raises(StorageError):
            layout.object_uri(Layer.BRONZE, "x", filename=bad)
