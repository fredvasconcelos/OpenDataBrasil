"""Séries de datasets no catálogo operacional (ADR-0016)."""

from pathlib import Path

from odb_catalog.ingestion import series_rows
from odb_ingestion import load_sources

SOURCES = Path(__file__).resolve().parents[3] / "configs" / "sources"


def test_series_without_own_dataset_get_a_catalog_row() -> None:
    rows = {r["id"]: r for r in series_rows(load_sources(SOURCES))}
    # O Sinesp VDE tem dataset real com o id da série (a página das notas).
    assert "mjsp-sinesp-vde" not in rows
    pof = rows["ibge-pof-despesa-familiar"]
    assert pof["oid"] == "2309, 1594, 6715"  # na ordem das edições (series_order)
    assert pof["ref"] == "https://sidra.ibge.gov.br/tabela/6715"  # a mais recente
    assert pof["lic"] == "ibge-reuso-com-citacao"
