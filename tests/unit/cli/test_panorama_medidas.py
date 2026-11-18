"""Confere medidas nativas, calendários e isolamento dos dados já carregados."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import httpx
import pytest

from odb_cli.panorama_gen import Generated
from odb_cli.panorama_medidas import (
    available_periods,
    generate_measures,
    measure_detail,
    measure_reference,
    validate_measure_support,
    validate_primary_support,
)
from odb_ingestion import HttpClient, load_sources
from odb_ingestion.config import HttpPolicy
from odb_ingestion.connectors.sidra import SidraConnector, shared_table_partition
from odb_semantics import load_panorama

CONFIGS = Path(__file__).parents[3] / "configs"


def test_calendario_do_vab_termina_em_2021() -> None:
    descriptor = json.loads((CONFIGS / "catalog/descritores/t5938.json").read_text())
    measure = next(v for v in descriptor["Variaveis"] if str(v["Id"]) == "498")
    periods = available_periods(descriptor, measure["PeriodoDisponibilidadeExcecao"])
    assert periods == [str(year) for year in range(2002, 2022)]
    with pytest.raises(ValueError, match="não reconhecida"):
        available_periods(descriptor, "1900 a 2021")


def test_selecao_preserva_medidas_unidades_e_totais_oficiais() -> None:
    generated = generate_measures(CONFIGS)
    assert len(generated.datasets) == len(generated.facts) == len(generated.indicators) == 142
    public = {k.id for _, _, k in generated.portal}
    assert len(public) == 118
    hidden = {i["id"] for i in generated.indicators} - public
    assert len(hidden) == 24
    assert all(i.startswith(("ic95_", "cv_")) for i in hidden)
    pairs = {(i["dataset"], i["variable"]) for i in generated.indicators}
    assert len(pairs) == 142
    for dataset, indicator in zip(generated.datasets, generated.indicators, strict=True):
        descriptor = json.loads(
            (CONFIGS / f"catalog/descritores/t{dataset['official_id']}.json").read_text()
        )
        measure = next(v for v in descriptor["Variaveis"] if str(v["Id"]) == indicator["variable"])
        assert indicator["unit"] == measure["UnidadeMedida"]
        assert dataset["params"]["variables"] == [indicator["variable"]]
        for classification in descriptor["Classificacoes"]:
            code = dataset["params"]["classifications"][f"c{classification['Id']}"]
            if (dataset["official_id"], classification["Id"]) in {("9552", 12404), ("7204", 892)}:
                assert set(code.split(",")) == {str(c["Id"]) for c in classification["Categorias"]}
                continue
            category = next(c for c in classification["Categorias"] if str(c["Id"]) == code)
            if dataset["official_id"] == "5932":
                assert category["Nome"] == "PIB a preços de mercado"
                assert code == "90707"
            elif dataset["official_id"] == "4277" and classification["Id"] == 58:
                assert code == "56742"
                assert category["Nome"] == "30 a 69 anos"
            elif classification["Id"] == 12716:
                assert category["Nome"] == "Total do trimestre"
            elif dataset["official_id"] == "6904":
                assert code == "33586"
                assert category["Nome"] == "Indústria geral"
            else:
                assert category["Nome"] == "Total"
        assert dataset["params"]["max_rows"] <= 50000
        assert set(dataset["params"]["periods"]) <= {
            str(p["Codigo"]) for p in descriptor["Periodos"]
        }


def test_novas_medidas_nao_substituem_variaveis_anteriores_na_silver() -> None:
    catalog = load_sources(CONFIGS / "sources")
    for dataset in catalog.datasets.values():
        if dataset.silver.get("panorama_support") is not True or dataset.silver.get("series"):
            continue
        params = SidraConnector.params(dataset)
        siblings = SidraConnector.siblings(catalog, dataset)
        assert siblings
        assert shared_table_partition(dataset.id, params, siblings) == ("variable_id",)


def test_referencia_exige_declaracao_e_categoria_existente() -> None:
    descriptor = json.loads((CONFIGS / "catalog/descritores/t5932.json").read_text())
    with pytest.raises(ValueError, match="sem Total comprovado"):
        measure_reference(descriptor, {})
    with pytest.raises(ValueError, match="referência c11255=0 inexistente"):
        measure_reference(descriptor, {"c11255": "0"})
    with pytest.raises(ValueError, match="classificações inexistentes"):
        measure_reference(descriptor, {"c1": "90707"})
    classes, fixed, periods, labels = measure_reference(descriptor, {"c11255": "90707"})
    assert classes == {"c11255": "90707"}
    assert fixed == {"Setores e subsetores": "90707"}
    assert periods[0] == "199601"
    assert labels == ["Setores e subsetores: PIB a preços de mercado (c11255=90707)"]
    category = next(c for c in descriptor["Classificacoes"][0]["Categorias"] if c["Id"] == 90707)
    category["PeriodoDisponibilidadeExcecao"] = "2º trimestre 1996 a 2º trimestre 2026"
    assert measure_reference(descriptor, {"c11255": "90707"})[2][0] == "199602"


def test_descoberta_do_comercio_exterior_nao_consulta_brasil() -> None:
    catalog = load_sources(CONFIGS / "sources")
    connector = SidraConnector(catalog.sources["ibge-sidra"], catalog.datasets_of("ibge-sidra"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/values/t/5945/n2/all/v/2152/p/all"
        return httpx.Response(200, json=[{"D3C": "Ano (Código)"}, {"D3C": "2015"}])

    with HttpClient(
        HttpPolicy(min_interval_s=0, max_attempts=1), transport=httpx.MockTransport(handler)
    ) as http:
        assert connector.discover_periods(catalog.datasets["ibge-medida-t5945-v2152"], http) == [
            "2015"
        ]


def test_n1_respeita_calendarios_unidades_e_nao_herda_regras_temporais() -> None:
    generated = generate_measures(CONFIGS)
    sources = {d["official_id"] + "/" + d["params"]["variables"][0]: d for d in generated.datasets}
    reference = sources["5932/6564"]["params"]
    assert reference["periods"][0] == "199602"
    assert reference["periods"][-1] == "202602"
    assert len(reference["periods"]) == 121
    assert sources["5932/6562"]["params"]["periods"][0] == "199601"
    assert sources["5932/6563"]["params"]["periods"][0] == "199601"
    for variable in ("2152", "2154"):
        params = sources[f"5945/{variable}"]["params"]
        assert params["periods"] == ["2013", "2014", "2015"]
        assert params["territorial_levels"] == ["n2", "n3"]
        assert params["period_discovery_level"] == "n2"
    for indicator in generated.indicators:
        if indicator["dataset"] in {
            s["id"] for p, s in sources.items() if p[:4] in {"6784", "5932", "5945"}
        }:
            assert "time_aggregation" not in indicator
    public = {k.id: k for _, _, k in generated.portal}
    assert public["pib_per_capita_v9812"].correcao is None
    assert public["variacao_pib_trimestral_v6563"].agregacao_tempo is None


def test_tabela_complementar_mantem_fonte_e_cobertura_proprias(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    (catalog / "descritores").symlink_to(CONFIGS / "catalog/descritores", target_is_directory=True)
    (catalog / "panorama.toml").symlink_to(CONFIGS / "catalog/panorama.toml")
    recipe = catalog / "medidas-adicionais.toml"
    content = "\n".join(
        [
            "[[measures]]",
            'parent = "pre_natal"',
            'table = "8288"',
            'variable = "6639"',
            'id = "pre_natal_v6639"',
            'label = "Mulheres que realizaram pré-natal (%)"',
            "publish = true",
        ]
    )
    recipe.write_text(content)
    result = generate_measures(tmp_path)
    assert result.datasets[0]["official_id"] == "8288"
    assert result.datasets[0]["params"]["territorial_levels"] == ["n1"]
    assert result.facts[0]["fixed_categories"] == {
        "Faixas de rendimento mensal domiciliar per capita": "32851"
    }
    recipe.write_text(content.replace('"8288"', '"8476"').replace('"6639"', '"11675"'))
    with pytest.raises(ValueError, match="tabela não declarada"):
        generate_measures(tmp_path)


def test_distribuicoes_alimentares_preservam_hierarquia_sem_somas() -> None:
    result = generate_measures(CONFIGS)
    entry = result.classifications["c12404ma"]
    assert set(entry["datasets"]) == {
        "ibge-medida-t9552-v9784",
        "ibge-medida-t9552-v10114",
        "ibge-medida-t9552-v10117",
    }
    assert entry["partitions"]["p109106"]["categories"] == ["109098", "109099"]
    assert entry["partitions"]["p109099"]["categories"] == ["109100", "109101", "109102"]
    assert all(not p["summable"] for p in entry["partitions"].values())
    for variable in ["9784", "10114", "10117"]:
        dataset = next(d for d in result.datasets if d["id"] == f"ibge-medida-t9552-v{variable}")
        assert dataset["params"]["classifications"] == {
            "c1": "6795",
            "c12404": "109106,109098,109099,109100,109101,109102",
        }
        fact = next(f for f in result.facts if f["dataset"] == dataset["id"])
        assert fact["fixed_categories"] == {"Situação do domicílio": "6795"}
        assert fact["classifications"] == {"c12404ma": "c12404ma_category_key"}
        assert result.dimensions[f"seguranca_alimentar_v{variable}"]["partition"] == "p109106"
    assert not result.map_share


def test_detalhe_recusa_niveis_e_calendarios_sem_prova() -> None:
    descriptor = json.loads((CONFIGS / "catalog/descritores/t9552.json").read_text())
    args: dict[str, Any] = {
        "dataset_id": "ibge-medida-t9552-v9784",
        "periods": ["2023", "2024"],
        "classes": {"c1": "6795", "c12404": "109106"},
        "fixed": {
            "Situação do domicílio": "6795",
            "Situação de segurança alimentar existente no domicílio": "109106",
        },
    }
    with pytest.raises(ValueError, match="contrato de níveis"):
        measure_detail(Generated(), descriptor, "c1", **args)
    with pytest.raises(ValueError, match="inexistente"):
        measure_detail(Generated(), descriptor, "c99999", **args)
    descriptor["Classificacoes"][1]["Categorias"][1]["PeriodoDisponibilidadeExcecao"] = "2024"
    with pytest.raises(ValueError, match="calendário próprio"):
        measure_detail(Generated(), descriptor, "c12404", **args)


def test_limites_de_ic95_ficam_ligados_a_estimativa_do_mesmo_recorte() -> None:
    items = tomllib.loads((CONFIGS / "catalog/medidas-adicionais.toml").read_text())["measures"]
    support = [item for item in items if item["id"].startswith("ic95_") and "support_of" in item]
    assert len(support) == 6
    validate_measure_support(items)
    for field, value in [
        ("publish", True),
        ("support_of", "estimativa_ausente"),
        ("table", "9552"),
        ("detail", "c12404"),
    ]:
        corrupted = [
            {**item, field: value} if item["id"] == support[0]["id"] else item for item in items
        ]
        with pytest.raises(ValueError, match="suporte"):
            validate_measure_support(corrupted)


def test_n3_preserva_coortes_e_cvs_sem_publicar_suporte_como_estimativa() -> None:
    generated = generate_measures(CONFIGS)
    datasets = {d["id"]: d for d in generated.datasets}
    public = {k.id: k for _, _, k in generated.portal}
    for variable, last in [("13235", "2021"), ("13236", "2020"), ("13237", "2019")]:
        params = datasets[f"ibge-medida-t9949-v{variable}"]["params"]
        assert params["periods"] == [str(year) for year in range(2017, int(last) + 1)]
        assert params["territorial_levels"] == ["n1"]
    for variable in ["10391", "10392", "10393"]:
        params = datasets[f"ibge-medida-t7204-v{variable}"]["params"]
        assert params["periods"] == ["2019", "2020", "2021", "2023", "2024"]
        assert params["classifications"] == {"c892": "47975,47976,47977"}
        assert f"cv_viagens_v{variable}" not in public
    assert "viagens_v10392" in public
    assert public["servicos_nao_financeiros_v635"].correcao is None
    assert public["industria_uf_v631"].agregacao_tempo is None


def test_cv_da_estimativa_principal_exige_variavel_oficial_e_fica_oculto() -> None:
    panorama = load_panorama(CONFIGS / "catalog/panorama.toml")
    parent = next(k for _, _, k in panorama.items() if k.id == "viagens")
    descriptor = json.loads((CONFIGS / "catalog/descritores/t7204.json").read_text())
    items = tomllib.loads((CONFIGS / "catalog/medidas-adicionais.toml").read_text())["measures"]
    item = next(i for i in items if i["id"] == "cv_viagens_v10391")
    validate_primary_support(item, parent, descriptor)
    invalid: list[dict[str, Any]] = [
        {"publish": True},
        {"support_of_primary": "10392"},
        {"table": "2581"},
    ]
    for changes in invalid:
        with pytest.raises(ValueError, match="suporte da variável principal"):
            validate_primary_support({**item, **changes}, parent, descriptor)
