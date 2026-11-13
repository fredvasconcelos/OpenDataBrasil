"""Gerador dos KPIs de Total do panorama (`odb panorama gerar`, ADR-0010)."""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from odb_cli.main import app
from odb_cli.panorama_gen import (
    generate,
    official_notes,
    official_source,
    pick_variable,
    render_indicators,
    render_portal,
    render_sources,
)
from odb_ingestion import load_sources
from odb_semantics import PanoramaKpi, check_against_acervo, load_panorama, load_scope
from odb_semantics.portal import load_portal

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
    """A mesma geração do comando (catálogo curado, fontes e descritores do repositório)."""
    from odb_cli.panorama import _generation  # noqa: PLC0415

    return _generation(load_panorama(PANORAMA), PANORAMA, CONFIGS, "demografia")


def test_generates_only_kpis_whose_value_is_the_total() -> None:  # noqa: PLR0915
    gen = _generate()
    ids = {i["id"]: i for i in gen.indicators}
    skipped = {k: why for k, _, why in gen.skipped}
    # A 9514 saiu (passou à 9606 curada); a 10061 entrou com uma classificação própria.
    assert len(ids) == 127
    # Variável fixada no panorama e regra automática (sem coeficientes de variação).
    assert ids["homicidios"]["variable"] == "13532"
    assert ids["taxa_escolarizacao"]["variable"] == "10276"
    # Total = universo: entra com as categorias; sem elas, fica de fora com o motivo.
    assert "plano_diretor" in ids
    # Total = universo com códigos próprios da tabela: classificação c1568t10061 (ADR-0014).
    assert gen.dimensions["nivel_instrucao_censo"]["classification"] == "c1568t10061"
    assert gen.classifications["c1568t10061"]["datasets"] == ["ibge-sidra-10061"]
    instrucao = next(d for d in gen.datasets if d["official_id"] == "10061")["params"]
    assert "c1568" in instrucao["classifications"]  # na fonte, o código SIDRA
    # Fora: sem Total, tabelas curadas, RM, unidade variável.
    # Sem Total: categoria de referência (parte B), com nota.
    assert "Bovino" in ids["efetivo_rebanhos"]["caveats"][0]
    pib = next(d for d in gen.datasets if d["official_id"] == "1846")
    assert pib["params"]["classifications"] == {"c11255": "90707"}  # PIB a preços de mercado
    assert "requer categoria de referência" in skipped["emissoes_gee"]
    assert "já configurada" in skipped["despesa_familiar"]
    assert "aquisicao_alimentar" not in skipped  # curada (POF de 1987 e 1995, ADR-0016)
    assert "unidade não é única" in skipped["producao_origem_animal"]
    assert "casamentos" in ids
    # Total + %: a dimensão principal vira classificação do fato; as demais ficam fixas.
    # Com a edição de 2010 (9841, ADR-0021), a 9543 vira série.
    fact = next(f for f in gen.facts if f["id"] == "fact_sidra_9543")
    assert fact["dataset"] == "ibge-serie-9543"
    # Sexo (principal, curada), cor ou raça e idade (detalhes marginais, ADR-0016). A idade
    # da 9543 tem faixas próprias: classificação c287t9543 (ADR-0014).
    assert fact["classifications"] == {
        "c2": "c2_category_key",
        "c86": "c86_category_key",
        "c287t9543": "c287t9543_category_key",
    }
    assert not {"Sexo", "Cor ou raça", "Idade"} & set(
        fact["table_rules"]["9543"]["fixed_categories"]
    )
    assert fact["table_rules"]["9841"]["missing_as_total"] == ["c86"]
    alfab = next(d for d in gen.datasets if d["official_id"] == "9543")["params"]
    # Requisição extra: sexo no Total, cor ou raça sem o Total (já vem na principal).
    assert alfab["extra_sets"][0] == {"c2": "6794", "c86": "2776,2777,2778,2779,2780"}
    assert list(alfab["extra_sets"][1]) == ["c2", "c287"]  # na fonte, o código SIDRA
    assert "extra_levels" not in alfab  # município liberado (ponto 7)
    assert [d["classification"] for d in gen.extra_dimensions["taxa_alfabetizacao_censo"]] == [
        "c86",
        "c287t9543",
    ]
    # Óbitos: sexo (Total 0 no Registro Civil: classificação própria), mês, local e idade
    # como detalhes marginais, até UF.
    assert [d["classification"] for d in gen.extra_dimensions["obitos"]] == [
        "c2t2654",
        "c244",
        "c257",
        "c260",
    ]
    # Tabelas-irmãs (ADR-0018): hipertensão (4418) ganha cor ou raça, idade, instrução,
    # rendimento e força de trabalho das irmãs 4419 a 4423, numa série com a base.
    assert gen.complements["hipertensao"] == ["4421", "4419", "4420", "4422", "4423"]
    hiper = next(f for f in gen.facts if f["id"] == "fact_sidra_4418")
    assert hiper["dataset"] == "ibge-serie-4418"
    assert "fixed_categories" not in hiper  # as fixas da base vão para a regra dela
    rule = hiper["table_rules"]["4421"]
    assert "c86" not in rule["missing_as_total"]  # a classificação da própria irmã
    assert "c86" in hiper["table_rules"]["4418"]["missing_as_total"]
    irma = next(d for d in gen.datasets if d["id"] == "ibge-sidra-4421")
    assert irma["silver"] == {
        "transformer": "sidra_observation",
        "territorial_reference": "ibge-dtb",
        "series": "ibge-serie-4418",
        "series_order": 1,
    }
    assert "95251" not in irma["params"]["classifications"]["c86"].split(",")  # sem o Total
    assert ids["hipertensao"]["dataset"] == "ibge-serie-4418"
    # Agregação no tempo declarada no panorama (ADR-0017).
    assert ids["vendas_materiais"]["time_aggregation"] == "mean"
    # IPCA pela variação mensal composta (ponto 15): o ano é a inflação do ano.
    assert ids["ipca"]["time_aggregation"] == "compound"
    assert ids["ipca"]["variable"] == "63"
    assert ids["abate_bovinos"]["time_aggregation"] == "sum"
    # Taxas: média com a ressalva de que não é a taxa oficial do período (ponto 14).
    assert ids["taxas_desocupacao"]["time_aggregation"] == "mean"
    assert any(c.startswith("Taxa: a média") for c in ids["taxas_desocupacao"]["caveats"])
    # Detalhe só nos níveis da nota da tabela (ponto 11): situação do domicílio na PNS.
    pns = next(d for d in gen.datasets if d["id"] == "ibge-sidra-4418")["params"]
    assert pns["extra_set_levels"] == [["n1"]]
    # Classe de tamanho do município: detalhe só até UF (cada município está numa classe).
    plano_params = next(d for d in gen.datasets if d["official_id"] == "5882")["params"]
    assert plano_params["extra_levels"] == ["n1", "n2", "n3"]
    plano = next(f for f in gen.facts if f["dataset"] == "ibge-sidra-5882")
    assert plano["classifications"] == {
        "c1480": "c1480_category_key",
        "c12446": "c12446_category_key",  # classe de tamanho do município (marginal)
    }
    assert gen.dimensions["plano_diretor"]["classification"] == "c1480"
    assert gen.classifications["c1480"]["total"] == "58278"  # "Total", do descritor
    # Município liberado em todas as séries (ponto 7): categorias em lotes de requisição.
    pam = next(d for d in gen.datasets if d["official_id"] == "5457")
    assert "detail_levels" not in pam["params"]
    assert pam["params"]["category_chunk"] == 7  # 7 culturas x ~5.600 territórios
    assert "," in pam["params"]["classifications"]["c782"]  # lista explícita, em lotes
    obitos = next(d for d in gen.datasets if d["official_id"] == "2654")
    assert "detail_levels" not in obitos["params"]
    assert obitos["params"]["category_chunk"] >= 1
    censo = next(d for d in gen.datasets if d["official_id"] == "9543")
    assert "detail_levels" not in censo["params"]
    assert "n6" in censo["params"]["territorial_levels"]
    # Sexo da PNS (110095/110096) entra como partição nova na c2 curada.
    assert "c2" in gen.extensions
    # Arranjos domiciliares: dimensão fixada no panorama (c460, não sexo do responsável).
    assert gen.dimensions["arranjos_domiciliares"]["classification"] == "c460"
    # Total no mesmo nível das categorias (lista plana): agrotóxicos por classe de uso.
    assert gen.dimensions["agrotoxicos"]["classification"] == "c716"
    # Total que a API não devolve por padrão: pedido explicitamente.
    agua = next(d for d in gen.datasets if d["official_id"] == "6731")
    assert agua["params"]["classifications"]["c825"] == "all"
    # Agregado único como Total ("15 anos ou mais") e níveis vindos do descritor.
    analf = next(d for d in gen.datasets if d["official_id"] == "7113")
    assert gen.dimensions["taxa_analfabetismo"]["classification"] == "c2"
    # O agregado "15 anos ou mais" (2795) é o Total da idade, que virou detalhe marginal
    # com faixas próprias da tabela (c58t7113): a requisição extra traz as faixas sem ele.
    assert gen.classifications["c58t7113"]["total"] == "2795"
    assert analf["params"]["classifications"]["c58"] == "2795"  # a principal segue no Total
    (extra,) = analf["params"]["extra_sets"]
    assert "c58" in extra
    assert "2795" not in extra["c58"].split(",")
    assert analf["params"]["territorial_levels"]
    # Sem Total nem agregado: categoria de referência (parte B).
    assert ids["vendas_varejo"]["variable"]  # índice de volume como referência
    # Total = universo: o mapa mostra o % da categoria principal.
    assert gen.map_share["plano_diretor"] == "58279"  # Com Plano Diretor
    assert "efetivo_rebanhos" not in gen.map_share
    # IPCA a partir de 1998 na Gold (a série inteira fica na Silver).
    assert ids["ipca"]["first_period"] == "1998"
    # Aditividade do descritor oficial (PermiteSomaUnidadesTerritoriais).
    assert ids["nascidos_vivos"]["additivity"] == "additive"
    assert ids["taxa_escolarizacao"]["additivity"] == "non_additive"
    # Mensal e trimestral: um ano por requisição, com o tipo do período.
    ipca = next(d for d in gen.datasets if d["official_id"] == "1737")
    assert ids["ipca"]["variable"] == "63"  # variação mensal (ponto 15)
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
    # Séries (silver.series, ADR-0016) contam como datasets: a POF reúne 2309, 1594 e 6715.
    series = {d.silver.get("series") for d in sources.datasets.values()} - {None}
    assert all(d in sources.datasets or d in series for d in catalog.datasets())
    assert {k.indicator for k in portal.kpis()} <= {i.id for i in catalog.indicators}
    assert len(portal.kpis()) == 14 + 127  # 14 curados no arquivo principal + 127 gerados


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


def test_official_source_is_plain_text_without_glued_blocks() -> None:
    # Descritor da tabela 6606: dois blocos <div>, entidades e ponto final.
    fonte = official_source(
        {
            "Fonte": "<div>Minist&eacute;rio da Sa&uacute;de, Informa&ccedil;&otilde;es sobre "
            "Mortalidade (SIM).</div> <div>Instituto Brasileiro de Geografia e Estat&iacute;stica."
            "</div>"
        }
    )
    assert fonte == (
        "Ministério da Saúde, Informações sobre Mortalidade (SIM). "
        "Instituto Brasileiro de Geografia e Estatística"
    )
    assert official_source(None) == ""


def test_generated_configs_have_no_html() -> None:
    """Nada de entidade ou marca HTML nos textos que vão à API e ao portal."""
    pattern = re.compile(r"&[a-zA-Z]+;|&#\d+;|</?(?:div|br|p|b|i|span|li)\b", re.IGNORECASE)
    found = [
        f"{path.name}:{n}"
        for path in sorted(Path("configs").rglob("*.toml"))
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if pattern.search(line)
    ]
    assert found == []


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
    assert "127 KPIs gerados (178 tabelas), 77 com categorias" in result.output
    assert "50 com detalhes marginais (117 classificações a mais)" in result.output
    assert "15 com tabelas-irmãs (49 tabelas)" in result.output  # ADR-0018
    data = tomllib.loads((tmp_path / "sources" / "ibge-panorama.toml").read_text("utf-8"))
    assert len(data["datasets"]) == 178  # 127 bases + 49 irmãs (ADR-0018) + 2 edições (ADR-0021)
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
    assert rows["populacao_sexo_idade"]["classification"] == "c86 Cor ou raça"  # 9606
    assert rows["populacao_sexo_idade"]["is_subject"] is False
    # Sem classificações: só o Total.
    assert rows["ipca"]["classification"] is None
    # Sem Total: o primeiro nível é o mais alto da hierarquia.
    assert rows["efetivo_rebanhos"]["has_total"] is False
    assert "Bovino" in rows["efetivo_rebanhos"]["categories"]
    doc = render_proposal(list(rows.values()), {"ipca"})
    assert doc.count("\n| ") == 156 + 1  # cabeçalho + 156 KPIs
    assert "c1480 Existência de Plano Diretor" in doc


def test_editions_bring_only_the_missing_periods() -> None:
    """Edições (ADR-0021): a 1209 traz 2022 para a série histórica da 1286."""
    gen = _generate()
    ed = next(d for d in gen.datasets if d["id"] == "ibge-sidra-1209")
    assert ed["params"]["periods"] == ["2022"]
    assert ed["params"]["variables"] == ["606"]  # a mesma variável da base
    assert ed["params"]["classifications"] == {"c58": "0"}  # idade fora do fato: Total
    assert ed["params"]["territorial_levels"] == ["n1", "n2", "n3"]
    assert ed["silver"]["series"] == "ibge-serie-1286"
    base = next(d for d in gen.datasets if d["id"] == "ibge-sidra-1286")
    assert base["silver"]["series_order"] == 2
    fact = next(f for f in gen.facts if f["id"] == "fact_sidra_1286")
    assert fact["dataset"] == "ibge-serie-1286"
    assert fact["table_rules"]["1209"]["fixed_categories"] == {"Grupo de idade": "0"}
    ind = next(i for i in gen.indicators if i["id"] == "populacao_nos_censos")
    assert ind["dataset"] == "ibge-serie-1286"
    assert any("2022 vêm da tabela 1209" in c for c in ind["caveats"])


def test_crossings_up_to_uf() -> None:
    """C1: óbitos (sexo x idade) cruzados até UF; no município, marginais."""
    gen = _generate()
    obitos = next(d for d in gen.datasets if d["official_id"] == "2654")["params"]
    (cross,) = obitos["cross_sets"]
    assert list(cross) == ["c1836", "c2", "c260"]
    assert cross["c1836"] == "0"  # a principal fora do cruzamento fica no Total
    assert "0" not in cross["c2"].split(",")  # sem os Totais (já vêm nos marginais)
    assert gen.crossed["obitos"] == [["c2t2654", "c260"]]
    portal = render_portal(gen, "demografia")
    assert 'crossed = [["c2t2654", "c260"]]' in portal
    ind = next(i for i in gen.indicators if i["id"] == "obitos")
    assert any("Cruzamentos completos" in c for c in ind["caveats"])


def test_multi_source_note_only_when_surveys_differ() -> None:
    """ADR-0022: a nota de fontes distintas aparece só quando a série junta pesquisas."""
    from odb_cli.panorama_gen import multi_source_note  # noqa: PLC0415

    censo = {"Pesquisa": "Censo Demográfico"}
    pnad = {"Pesquisa": "Pesquisa Nacional por Amostra de Domicílios Contínua anual"}
    assert multi_source_note("6805", censo, {"9841": censo}) == ""
    note = multi_source_note("6805", censo, {"7192": pnad})
    assert "Fontes distintas (ADR-0022)" in note
    assert "Censo Demográfico (tabela 6805)" in note
    assert "Contínua anual (tabela 7192)" in note


def test_crossing_only_where_all_details_exist() -> None:
    """Pré-natal (8289): situação do domicílio só no Brasil (nota); o cruzamento também."""
    gen = _generate()
    params = next(d for d in gen.datasets if d["official_id"] == "8289")["params"]
    assert params["cross_sets"] == [{"c86": "2776,2777,2779", "c1": "1,2"}]
    assert params["cross_levels"] == ["n1"]
    assert 'crossed_levels = ["brasil"]' in render_portal(gen, "demografia")
