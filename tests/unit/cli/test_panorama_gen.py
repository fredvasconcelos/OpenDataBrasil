"""Gerador dos KPIs de Total do panorama (`odb panorama gerar`, ADR-0010)."""

from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from odb_api.portal import load_portal
from odb_cli.main import app
from odb_cli.panorama_gen import (
    generate,
    official_notes,
    pick_variable,
    render_indicators,
    render_portal,
    render_sources,
)
from odb_ingestion import load_sources
from odb_semantics import PanoramaKpi, check_against_acervo, load_panorama, load_scope

REPO = Path(__file__).resolve().parents[3]
CONFIGS = REPO / "configs"
PANORAMA = CONFIGS / "catalog" / "panorama.toml"


def _inputs() -> tuple[Any, dict[str, Any], dict[str, str], dict[str, Any]]:
    config = load_panorama(PANORAMA)
    titles = check_against_acervo(config, PANORAMA.parent / config.acervo)
    verification = json.loads((PANORAMA.parent / "panorama_verificacao.json").read_text("utf-8"))
    descriptors = {
        p.stem[1:]: json.loads(p.read_text("utf-8"))
        for p in (PANORAMA.parent / "descritores").glob("t*.json")
    }
    return config, verification, titles, descriptors


def _generate() -> Any:
    config, verification, titles, descriptors = _inputs()
    return generate(
        config,
        verification,
        titles,
        configured_tables={"9605": "ibge-sidra-9605", "6715": "ibge-sidra-6715"},
        existing_indicators=[],
        existing_portal_kpis=[],
        descriptors=descriptors,
    )


def test_generates_only_kpis_whose_value_is_the_total() -> None:
    gen = _generate()
    ids = {i["id"]: i for i in gen.indicators}
    skipped = {k: why for k, _, why in gen.skipped}
    assert len(ids) == 92
    # Variável fixada no panorama e regra automática (sem coeficientes de variação).
    assert ids["homicidios"]["variable"] == "13532"
    assert ids["taxa_escolarizacao"]["variable"] == "10276"
    # Fora: Total = universo, sem Total, períodos não anuais, tabelas curadas, RM.
    assert "entra com as categorias" in skipped["plano_diretor"]
    assert "sem categoria Total" in skipped["efetivo_rebanhos"]
    assert "sem categoria Total" in skipped["vendas_varejo"]  # mensal, mas sem Total
    assert "já configurada" in skipped["despesa_familiar"]
    assert "n7" in skipped["aquisicao_alimentar"]
    assert "unidade não é única" in skipped["producao_origem_animal"]
    assert "casamentos" in ids
    # Classificações do Total viram categorias fixas, com o código observado na fonte.
    fact = next(f for f in gen.facts if f["dataset"] == "ibge-sidra-9514")
    assert fact["fixed_categories"]["Sexo"] == "6794"
    # Aditividade do descritor oficial (PermiteSomaUnidadesTerritoriais).
    assert ids["nascidos_vivos"]["additivity"] == "additive"
    assert ids["taxa_escolarizacao"]["additivity"] == "non_additive"
    # Mensal e trimestral: um ano por requisição, com o tipo do período.
    ipca = next(d for d in gen.datasets if d["official_id"] == "1737")
    assert ids["ipca"]["variable"] == "2265"  # variação acumulada em 12 meses
    assert ipca["params"]["period_type"] == "mes"
    assert ipca["params"]["group_periods_by_year"] is True
    assert ipca["params"]["max_rows"] == 12
    pnad = next(d for d in gen.datasets if d["official_id"] == "4093")
    assert pnad["params"]["period_type"] == "trimestre"
    # Município da PNAD trimestral = 27 capitais (recorte), não o país inteiro.
    assert pnad["params"]["max_rows"] < 4 * 1000
    # Tabela sem nível Brasil: apresentada como publicada, com nota.
    ds = next(d for d in gen.datasets if d["official_id"] == "10457")
    assert ds["params"]["territorial_levels"] == ["n3"]
    assert ds["params"]["period_discovery_level"] == "n3"
    assert any("não publica esta tabela para o Brasil" in c for c in ids["industria_uf"]["caveats"])


def test_rendered_fragments_load_with_the_curated_configs(tmp_path: Path) -> None:
    gen = _generate()
    for sub in ("sources", "indicators", "portal"):
        (tmp_path / sub / "demografia").mkdir(parents=True)
    shutil.copy(CONFIGS / "sources" / "ibge.toml", tmp_path / "sources")
    (tmp_path / "sources" / "gen.toml").write_text(render_sources(gen), "utf-8")
    shutil.copy(CONFIGS / "indicators" / "demografia.toml", tmp_path / "indicators")
    shutil.copy(
        CONFIGS / "indicators" / "demografia" / "pof.toml", tmp_path / "indicators" / "demografia"
    )
    (tmp_path / "indicators" / "demografia" / "gen.toml").write_text(
        render_indicators(gen, "demografia"), "utf-8"
    )
    shutil.copy(CONFIGS / "portal" / "demografia.toml", tmp_path / "portal")
    (tmp_path / "portal" / "demografia" / "gen.toml").write_text(
        render_portal(gen, "demografia"), "utf-8"
    )
    sources = load_sources(tmp_path / "sources")
    catalog = load_scope(tmp_path / "indicators", "demografia")
    portal = load_portal(tmp_path / "portal", "demografia")
    assert all(d in sources.datasets for d in catalog.datasets())
    assert {k.indicator for k in portal.kpis()} <= {i.id for i in catalog.indicators}
    assert len(portal.kpis()) == 13 + 92


def test_repository_fragments_are_up_to_date() -> None:
    gen = _generate()
    assert (CONFIGS / "sources" / "ibge-panorama.toml").read_text("utf-8") == render_sources(gen)
    assert (CONFIGS / "indicators" / "demografia" / "panorama.toml").read_text(
        "utf-8"
    ) == render_indicators(gen, "demografia")
    assert (CONFIGS / "portal" / "demografia" / "panorama.toml").read_text(
        "utf-8"
    ) == render_portal(gen, "demografia")


def test_variable_rules() -> None:
    kpi = PanoramaKpi(id="x", label="X", tabela="1", pesquisa="P")
    info = {
        "variables": [
            {"id": "1", "name": "Coeficiente de variação - X", "units": ["%"]},
            {"id": "2", "name": "X", "units": ["Pessoas"]},
        ]
    }
    assert pick_variable(kpi, info)[0]["id"] == "2"  # type: ignore[index]
    fixed = kpi.model_copy(update={"variavel": "9"})
    assert "não existe" in pick_variable(fixed, info)[1]
    info["variables"][1]["units"] = ["Mil Cruzeiros", "Mil Reais"]
    assert "unidade não é única" in pick_variable(kpi, info)[1]


def test_official_notes_are_plain_text() -> None:
    notes = official_notes(
        {"Nota": "1 -&nbsp;Dados <b>do</b> Universo.<br />2 - A&ccedil;&atilde;o."}
    )
    assert notes == ["1 - Dados do Universo.", "2 - Ação."]
    assert official_notes(None) == []


def test_gerar_command_writes_three_fragments(tmp_path: Path) -> None:
    for sub in ("sources", "indicators", "portal"):
        shutil.copytree(CONFIGS / sub, tmp_path / sub)
    for path in (
        tmp_path / "sources" / "ibge-panorama.toml",
        tmp_path / "indicators" / "demografia" / "panorama.toml",
        tmp_path / "portal" / "demografia" / "panorama.toml",
    ):
        path.unlink()
    result = CliRunner().invoke(app, ["panorama", "gerar", "--raiz", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "92 KPIs de Total gerados" in result.output
    data = tomllib.loads((tmp_path / "sources" / "ibge-panorama.toml").read_text("utf-8"))
    assert len(data["datasets"]) == 92
    assert "institution" not in data


@pytest.mark.parametrize("table", ["3926", "6715"])
def test_descriptors_are_versioned_with_checksum(table: str) -> None:
    import hashlib  # noqa: PLC0415

    index = json.loads((PANORAMA.parent / "descritores" / "indice.json").read_text("utf-8"))
    raw = (PANORAMA.parent / "descritores" / f"t{table}.json").read_bytes()
    assert index[table]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert str(json.loads(raw)["Id"]) == table


def test_paused_kpi_keeps_dataset_for_retry() -> None:
    config, verification, titles, descriptors = _inputs()
    paused = config.model_copy(
        update={
            "temas": tuple(
                t.model_copy(
                    update={
                        "subtemas": tuple(
                            s.model_copy(
                                update={
                                    "kpis": tuple(
                                        k.model_copy(update={"pausado": "timeout na fonte"})
                                        if k.id == "casamentos"
                                        else k
                                        for k in s.kpis
                                    )
                                }
                            )
                            for s in t.subtemas
                        )
                    }
                )
                for t in config.temas
            )
        }
    )
    gen = generate(
        paused,
        verification,
        titles,
        configured_tables={},
        existing_indicators=[],
        existing_portal_kpis=[],
        descriptors=descriptors,
    )
    skipped = {k: why for k, _, why in gen.skipped}
    # Em espera: o dataset continua nas fontes (para repescar), fora do catálogo e do portal.
    assert skipped["casamentos"] == "em espera: timeout na fonte"
    assert "ibge-sidra-4412" in {d["id"] for d in gen.datasets}
    assert "ibge-sidra-4412" not in {f["dataset"] for f in gen.facts}


def test_proposal_of_main_dimension_from_descriptors() -> None:
    from odb_cli.panorama_gen import propose_dimensions, render_proposal  # noqa: PLC0415

    config, _, _, descriptors = _inputs()
    rows = {r["kpi"]: r for r in propose_dimensions(config, descriptors)}
    # Assunto da tabela: a existência do Plano Diretor, não o tamanho do município.
    assert rows["plano_diretor"]["classification"] == "c1480 Existência de Plano Diretor"
    assert rows["plano_diretor"]["categories"] == ["Com Plano Diretor", "Sem Plano Diretor"]
    assert rows["plano_diretor"]["sums"] is True
    # Só recortes comuns: o primeiro deles, marcado como tal.
    assert rows["populacao_sexo_idade"]["classification"] == "c2 Sexo"
    assert rows["populacao_sexo_idade"]["is_subject"] is False
    # Sem classificações: só o Total.
    assert rows["ipca"]["classification"] is None
    # Sem Total: o primeiro nível é o mais alto da hierarquia.
    assert rows["efetivo_rebanhos"]["has_total"] is False
    assert "Bovino" in rows["efetivo_rebanhos"]["categories"]
    doc = render_proposal(list(rows.values()), {"ipca"})
    assert doc.count("\n| ") == 150 + 1  # cabeçalho + 150 KPIs
    assert "c1480 Existência de Plano Diretor" in doc
