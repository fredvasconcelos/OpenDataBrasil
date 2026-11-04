from pathlib import Path

import pytest

from odb_ingestion import ConfigError, build_connectors, load_sources
from tests.ingestion_support import TEST_SOURCES

REPO_SOURCES = Path(__file__).parents[3] / "configs" / "sources"


def test_repository_sources_are_valid() -> None:
    catalog = load_sources(REPO_SOURCES)
    assert set(catalog.datasets) == {
        "ibge-sidra-6579",
        "ibge-sidra-4714",
        "ibge-sidra-9605",
        "ibge-sidra-9718",
        "ibge-sidra-9578",
        "ibge-sidra-9971",
        "ibge-sidra-9970",
        "ibge-sidra-9723",
        "ibge-sidra-9954",
        "ibge-dtb",
    }
    assert catalog.source_institution["ibge-sidra"] == "ibge"
    assert catalog.licenses["ibge-reuso-com-citacao"].review_status == "requires_review"
    assert set(build_connectors(catalog)) == {"ibge-sidra", "ibge-geoftp"}
    assert [d.id for d in catalog.datasets_of("ibge-geoftp")] == ["ibge-dtb"]


def test_config_checksum_is_stable_and_sensitive() -> None:
    a = load_sources(TEST_SOURCES).dataset("ibge-dtb")
    b = load_sources(TEST_SOURCES).dataset("ibge-dtb")
    assert a.config_sha256() == b.config_sha256()
    assert a.model_copy(update={"title": "x"}).config_sha256() != a.config_sha256()


def _write(tmp_path: Path, name: str, body: str) -> Path:
    (tmp_path / name).write_text(body, encoding="utf-8")
    return tmp_path


BASE = """
config_version = "1"
[institution]
id = "inst"
name = "n"
acronym = "N"
url = "https://x"
[[licenses]]
id = "lic"
name = "l"
conditions = "c"
review_status = "approved"
[[sources]]
id = "src"
name = "s"
connector = "http_file"
base_url = "https://x/"
"""

DATASET = """
[[datasets]]
id = "ds"
source = "{source}"
official_id = "1"
title = "t"
description = "d"
license = "{license}"
access_classification = "public_authorized"
periodicity = "anual"
[datasets.params]
url = "https://x/f.zip"
artifact_name = "f.zip"
"""


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (BASE + DATASET.format(source="nope", license="lic"), "fonte desconhecida"),
        (BASE + DATASET.format(source="src", license="nope"), "licença desconhecida"),
        ("not toml = = =", "inst.toml"),
        (BASE.replace('id = "src"', 'id = "Bad Id"'), "inst.toml"),
    ],
)
def test_invalid_files_rejected(tmp_path: Path, body: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_sources(_write(tmp_path, "inst.toml", body))


def test_duplicates_across_files_and_unknowns(tmp_path: Path) -> None:
    _write(tmp_path, "a.toml", BASE + DATASET.format(source="src", license="lic"))
    _write(tmp_path, "b.toml", BASE)
    with pytest.raises(ConfigError, match="duplicada"):
        load_sources(tmp_path)
    with pytest.raises(ConfigError, match="nenhum arquivo"):
        load_sources(tmp_path / "vazio")


def test_unknown_connector_and_bad_params(tmp_path: Path) -> None:
    catalog = load_sources(_write(tmp_path, "a.toml", BASE.replace("http_file", "ftp")))
    with pytest.raises(ConfigError, match="tipo de conector desconhecido"):
        build_connectors(catalog)
    with pytest.raises(ConfigError, match="não configurado"):
        catalog.dataset("x")
    body = BASE + DATASET.format(source="src", license="lic").replace("https://x/f.zip", "http://x")
    with pytest.raises(ConfigError, match="http_file inválidos"):
        build_connectors(load_sources(_write(tmp_path, "a.toml", body)))
