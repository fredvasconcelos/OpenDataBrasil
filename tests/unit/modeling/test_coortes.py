"""Coortes SIDRA compartilham a tabela sem multiplicar ou perder observações."""

from pathlib import Path

import polars as pl
import pytest

from odb_ingestion import load_sources
from odb_modeling import model
from odb_modeling.builder import _shared_filter
from odb_modeling.model import DatasetInfo
from odb_processing.contracts import SIDRA_OBSERVATION
from tests.gold_support import GoldEnv


def test_tabela_repetida_na_serie_entra_uma_vez_no_mapa() -> None:
    info = DatasetInfo("serie", "5457", None, "ibge", table_ids=("5457", "5457"))
    assert info.source_tables == ("5457",)


def test_coortes_da_mesma_tabela_formam_uniao_dos_recortes() -> None:
    frame = pl.DataFrame(
        {
            "table_id": ["5457", "5457", "5457", "5457", "74", "74"],
            "id": ["a", "b", "c", "d", "e", "f"],
            "classifications": [
                [{"category_id": c} for c in group]
                for group in [("1", "6794"), ("3",), ("99",), ("1",), ("5",), ("6",)]
            ],
        }
    )
    shared = (("5457", (("1", "2"), ("6794",))), ("5457", (("3",),)), ("74", (("5",),)))
    assert frame.filter(_shared_filter(shared))["id"].to_list() == ["a", "b", "e"]


@pytest.mark.parametrize("uri_count", [1, 2])
def test_leitura_silver_preserva_todos_os_membros_sem_multiplicar_tabela(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, uri_count: int
) -> None:
    """Exercita o scan real da Gold com as seis coortes de área colhida da 5457."""
    sources = load_sources(Path(__file__).parents[3] / "configs/sources")
    series = "ibge-agro-5457-216-ha"
    members = sources.series_of(series)
    assert len(members) == 6
    gold = GoldEnv(tmp_path).gold
    monkeypatch.setattr(gold, "_sources", sources)
    info = gold._sidra_series_info(series, [sources.dataset(m) for m in members])
    uris = [f"file:///silver/teste-{i}" for i in range(uri_count)]
    columns = SIDRA_OBSERVATION.schema
    frame = pl.DataFrame({"table_id": ["5457", "74"]}).with_columns(
        pl.lit(None, dtype=columns[c]).alias(c) for c in model.SILVER_COLUMNS if c != "table_id"
    )
    calls: list[tuple[str, int]] = []

    def scan(uri: str, version: int) -> pl.LazyFrame:
        calls.append((uri, version))
        return frame.lazy()

    monkeypatch.setattr(gold._reader, "scan", scan)
    inputs = {
        "datasets": {m: {"uri": uris[i % uri_count]} for i, m in enumerate(members)},
        "silver": dict.fromkeys(uris, 602),
    }
    result = gold._silver_scan(inputs, {series: info}).collect()
    assert result["table_id"].to_list() == ["5457"] * uri_count
    assert calls == [(uri, 602) for uri in uris]
    assert info.source_tables == ("5457",)
