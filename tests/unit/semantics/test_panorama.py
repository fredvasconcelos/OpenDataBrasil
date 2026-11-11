"""Panorama do Brasil (configs/catalog/panorama.toml, ADR-0010)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from odb_semantics import (
    PanoramaConfigError,
    check_against_acervo,
    check_against_portal,
    load_panorama,
    read_acervo,
    resolve_links,
)

REPO = Path(__file__).resolve().parents[3]
CATALOG = REPO / "configs" / "catalog"
PANORAMA = CATALOG / "panorama.toml"
BASE = PANORAMA.read_text(encoding="utf-8")


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "panorama.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_repository_panorama_is_valid() -> None:
    panorama = load_panorama(PANORAMA)
    assert len(panorama.temas) == 20
    assert len(panorama.subthemes()) == 64
    assert len(panorama.items()) == 150
    assert sum(k.kpi is not None for _, _, k in panorama.items()) == 12
    # Variáveis fixadas e KPIs cujo Total é só o universo (esperam as categorias).
    by_id = {k.id: k for _, _, k in panorama.items()}
    assert by_id["homicidios"].variavel == "13532"
    assert sum(k.requer_categoria for k in by_id.values()) == 19
    # Filtros se adaptam ao tema: sem cor ou raça na agropecuária.
    agro = next(t for t in panorama.temas if t.id == "agropecuaria")
    assert "cor_raca" not in agro.filtros


def test_repository_panorama_matches_acervo_snapshot() -> None:
    panorama = load_panorama(PANORAMA)
    titles = check_against_acervo(panorama, CATALOG / panorama.acervo)
    assert len(titles) == len(panorama.tables())
    assert titles["417"].startswith("Aquisição (monetária) alimentar domiciliar per capita")


def test_repository_panorama_covers_portal() -> None:
    portal = tomllib.loads((REPO / "configs" / "portal" / "demografia.toml").read_text("utf-8"))
    kpis = {k["id"]: k for t in portal["themes"] for s in t["subthemes"] for k in s["kpis"]}
    check_against_portal(load_panorama(PANORAMA), kpis)
    with pytest.raises(PanoramaConfigError, match="fora do panorama"):
        check_against_portal(load_panorama(PANORAMA), {**kpis, "novo": {}})
    del kpis["populacao_estimada"]
    with pytest.raises(PanoramaConfigError, match="inexistentes no portal"):
        check_against_portal(load_panorama(PANORAMA), kpis)


def test_links_by_explicit_kpi_or_item_id() -> None:
    panorama = load_panorama(PANORAMA)
    links = resolve_links(panorama, ["populacao_estimada", "crescimento_populacional"])
    assert links["populacao_estimada"] == "populacao_estimada"  # explícito
    assert links["crescimento_populacional"] == "crescimento_populacional"  # pelo id
    assert links["envelhecimento"] is None  # planejado
    kpis: dict[str, object] = {"crescimento_populacional": {}}
    with pytest.raises(PanoramaConfigError, match="inexistentes"):
        check_against_portal(panorama, kpis)


def test_acervo_reader_has_no_header(tmp_path: Path) -> None:
    path = tmp_path / "acervo.csv"
    path.write_bytes("﻿1278;Agroindústria rural\r\n417;Aquisição; com ponto e vírgula\r\n".encode())
    tables, digest = read_acervo(path)
    assert tables == {"1278": "Agroindústria rural", "417": "Aquisição"}
    assert len(digest) == 64


def test_acervo_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "acervo.csv"
    path.write_text("417;Aquisição\n", encoding="utf-8")
    with pytest.raises(PanoramaConfigError, match="SHA-256") as err:
        check_against_acervo(load_panorama(PANORAMA), path)
    assert "tabelas ausentes" in str(err.value)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('id = "envelhecimento"', 'id = "populacao_estimada"', "KPI repetido"),
        ('id = "lixo"', 'id = "agua"', "subtema repetido"),
        ('filtros = ["produto", "especie"]', 'filtros = ["produto", "raca"]', "não declarados"),
        (
            'tabela = "5457", pesquisa = "Produção Agrícola Municipal", filtros = ["produto"]',
            'tabela = "5457", pesquisa = "Produção Agrícola Municipal", filtros = ["cor_raca"]',
            "fora do tema agropecuaria",
        ),
        ('tabela = "417"', 'tabela = "0417"', "tabela"),
        ('kpi = "area_territorial"', 'kpi = "populacao_estimada"', "kpi do portal repetido"),
    ],
)
def test_structure_errors(tmp_path: Path, old: str, new: str, message: str) -> None:
    assert old in BASE
    with pytest.raises(PanoramaConfigError, match=message):
        load_panorama(_write(tmp_path, BASE.replace(old, new, 1)))


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(PanoramaConfigError, match="inválido"):
        load_panorama(tmp_path / "nada.toml")
