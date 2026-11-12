"""Conversão do Sinesp VDE (MJSP) para observações da Silver, com linhas sintéticas."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import polars as pl
import pytest

from odb_processing.parsers import Lineage, ParseError
from odb_processing.quality import CheckStatus, sinesp_checks
from odb_processing.sinesp import COLUMNS, VdeReport, normalize_name, sinesp_observations, slug

LINEAGE = Lineage(
    "a", "b" * 64, "https://x/bancovde-2023.xlsx", datetime.now(UTC), "i", "r", datetime.now(UTC)
)
UF_CODES = {"AC": "12", "SP": "35"}
MUNICIPALITIES = {
    ("AC", "RIO BRANCO"): "1200401",
    ("SP", "SANTA BARBARA DOESTE"): "3545803",
}


def _row(**kw: object) -> dict[str, object]:
    base: dict[str, object] = dict.fromkeys(COLUMNS)
    base |= {"abrangencia": "Estadual", "data_referencia": date(2023, 1, 1)}
    return base | kw


RAW = pl.DataFrame(
    [
        # Homicídio (vítimas, por sexo), em duas linhas da mesma chave: devem ser somadas.
        _row(
            uf="AC",
            municipio="RIO BRANCO",
            evento="Homicídio doloso",
            feminino=1,
            masculino=3,
            nao_informado=0,
            total_vitima=4,
        ),
        _row(
            uf="AC",
            municipio="RIO BRANCO",
            evento="Homicídio doloso",
            feminino=0,
            masculino=1,
            nao_informado=0,
            total_vitima=1,
        ),
        # Grafia com acento e apóstrofo casa com a DTB pelo nome normalizado.
        _row(
            uf="SP",
            municipio="SANTA BÁRBARA D'OESTE",
            evento="Homicídio doloso",
            feminino=0,
            masculino=0,
            nao_informado=0,
            total_vitima=0,
        ),
        # Município sem correspondência: entra só na UF e vai para o relatório.
        _row(
            uf="SP",
            municipio="CIDADE INEXISTENTE",
            evento="Homicídio doloso",
            feminino=0,
            masculino=2,
            nao_informado=0,
            total_vitima=2,
        ),
        # Evento só por UF, com PF: abrangência entra como dimensão; valor ausente na PF.
        _row(uf="SP", municipio="NÃO INFORMADO", evento="Roubo de veículo", total=10),
        _row(
            uf="SP",
            municipio="NÃO INFORMADO",
            evento="Roubo de veículo",
            abrangencia="Polícia Federal",
            total=None,
        ),
        # Furto: estadual vazia (indisponível) e PF informada.
        _row(uf="SP", municipio="NÃO INFORMADO", evento="Furto de veículo", total=None),
        _row(
            uf="SP",
            municipio="NÃO INFORMADO",
            evento="Furto de veículo",
            abrangencia="Polícia Federal",
            total=2,
        ),
        # Peso (kg, ponto decimal).
        _row(uf="SP", municipio="NÃO INFORMADO", evento="Apreensão de Cocaína", total_peso="63.12"),
        # Arma apreendida: dimensão Arma.
        _row(
            uf="AC",
            municipio="NÃO INFORMADO",
            evento="Arma de Fogo Apreendida",
            arma="Pistola",
            total=3,
        ),
        _row(
            uf="AC",
            municipio="NÃO INFORMADO",
            evento="Arma de Fogo Apreendida",
            arma="Fuzil",
            total=1,
        ),
    ],
    schema=COLUMNS,
)


def _convert() -> tuple[pl.DataFrame, VdeReport]:
    return sinesp_observations(
        RAW,
        year="2023",
        uf_codes=UF_CODES,
        municipalities=MUNICIPALITIES,
        table_id="SINESP-VDE-2023",
        lineage=LINEAGE,
    )


def _value(
    frame: pl.DataFrame, variable: str, level: str, territory: str, key: str
) -> tuple[Any, Any, Any]:
    row = frame.filter(
        (pl.col("variable_id") == variable)
        & (pl.col("territorial_level") == level)
        & (pl.col("territory_id") == territory)
        & (pl.col("classification_key") == key)
    )
    assert row.height == 1, (variable, level, territory, key, row.height)
    return row["value"][0], row["value_status"][0], row["value_raw"][0]


def test_names_and_slugs() -> None:
    assert normalize_name("Santa Bárbara d'Oeste") == "SANTA BARBARA DOESTE"
    assert normalize_name("Biritiba-Mirim") == "BIRITIBA MIRIM"
    assert slug("Roubo seguido de morte (latrocínio)") == "roubo-seguido-de-morte-latrocinio"


def test_victims_by_municipality_sum_duplicates_and_sex() -> None:
    out, report = _convert()
    hom = "homicidio-doloso"
    assert _value(out, hom, "6", "1200401", "Sexo=T")[0] == 5  # duas linhas somadas
    assert _value(out, hom, "6", "1200401", "Sexo=masculino")[0] == 4
    assert _value(out, hom, "6", "1200401", "Sexo=feminino")[0] == 1
    # Zero informado é zero verdadeiro (não arredondamento).
    assert _value(out, hom, "6", "3545803", "Sexo=T")[1] == "true_zero"
    # UF inclui o município sem correspondência na DTB.
    assert _value(out, hom, "3", "35", "Sexo=T")[0] == 2
    # Brasil derivado: soma das UFs (5 no AC + 2 em SP).
    assert _value(out, hom, "1", "1", "Sexo=T")[0] == 7
    assert _value(out, hom, "1", "1", "Sexo=masculino")[0] == 6
    assert "3500000" not in out["territory_id"].to_list()
    assert report.unmatched == {"SP/CIDADE INEXISTENTE": 1}
    assert report.duplicated_keys == 1
    assert out.filter(pl.col("variable_id") == hom)["unit_name"].unique().to_list() == ["Vítimas"]


def test_uf_events_federal_scope_and_missing_values() -> None:
    out, report = _convert()
    roubo = "roubo-de-veiculo"
    # PF vazia no ano inteiro: não se aplica, sai da soma. Sobra só a estadual, então a
    # abrangência deixa de ser dimensão do evento (repetiria o Total).
    assert _value(out, roubo, "3", "35", "")[0] == 10
    assert report.federal_empty == {"Roubo de veículo": ["SP"]}
    # Estadual ausente com PF informada: o total fica ausente ("...", nunca 0 nem parcial).
    value, status, raw = _value(out, "furto-de-veiculo", "3", "35", "Abrangência=T")
    assert (value, status, raw) == (None, "not_available", "...")
    assert _value(out, "furto-de-veiculo", "3", "35", "Abrangência=policia-federal")[0] == 2
    # "NÃO INFORMADO" não gera município.
    assert sorted(out.filter(pl.col("variable_id") == roubo)["territorial_level"].unique()) == [
        "1",
        "3",
    ]


def test_weight_and_row_dimensions() -> None:
    out, report = _convert()
    value, status, _ = _value(out, "apreensao-de-cocaina", "3", "35", "")
    assert float(value) == pytest.approx(63.12)
    assert status == "valid"
    arma = out.filter(
        (pl.col("variable_id") == "arma-de-fogo-apreendida") & (pl.col("territorial_level") == "3")
    )
    assert sorted(arma["classification_key"].to_list()) == ["Arma=T", "Arma=fuzil", "Arma=pistola"]
    assert arma["unit_name"].unique().to_list() == ["Armas"]
    # Homicídio só estadual: a abrangência não entra (repetiria o Total).
    hom = out.filter(pl.col("variable_id") == "homicidio-doloso")["classification_key"]
    assert not hom.str.contains("Abrangência").any()
    assert report.events["Apreensão de Cocaína"] == "peso"
    checks = {c.check_id: c.status for c in sinesp_checks(report)}
    assert checks["sinesp.municipality_names"] is CheckStatus.WARN
    assert checks["sinesp.duplicated_keys"] is CheckStatus.WARN


def test_periods_and_validation() -> None:
    out, _ = _convert()
    assert out["period"].unique().to_list() == ["202301"]
    assert out["period_name"].unique().to_list() == ["janeiro 2023"]
    with pytest.raises(ParseError, match="outros anos"):
        sinesp_observations(
            RAW, year="2022", uf_codes=UF_CODES, municipalities=MUNICIPALITIES,
            table_id="t", lineage=LINEAGE,
        )  # fmt: skip
    with pytest.raises(ParseError, match="UF desconhecida"):
        sinesp_observations(
            RAW, year="2023", uf_codes={"AC": "12"}, municipalities=MUNICIPALITIES,
            table_id="t", lineage=LINEAGE,
        )  # fmt: skip


# Os 31 eventos da planilha oficial (bancovde-2023.xlsx, conferidos em 2026-11-12).
EVENTS = {
    "Apreensão de Cocaína", "Apreensão de Maconha", "Arma de Fogo Apreendida",
    "Atendimento pré-hospitalar", "Busca e salvamento", "Combate a incêndios",
    "Emissão de Alvarás de licença", "Estupro", "Estupro de vulnerável", "Feminicídio",
    "Furto de veículo", "Homicídio doloso", "Lesão corporal seguida de morte",
    "Mandado de prisão cumprido", "Morte de Agente do Estado",
    "Morte no trânsito ou em decorrência dele (exceto homicídio doloso)",
    "Morte por intervenção de Agente do Estado", "Mortes a esclarecer (sem indício de crime)",
    "Mortes no trânsito", "Pessoa Desaparecida", "Pessoa Localizada", "Realização de vistorias",
    "Roubo a instituição financeira", "Roubo de carga", "Roubo de veículo",
    "Roubo seguido de morte (latrocínio)", "Suicídio", "Suicídio de Agente do Estado",
    "Tentativa de feminicídio", "Tentativa de homicídio", "Tráfico de drogas",
}  # fmt: skip


def test_repository_coverage_table_uses_real_event_names() -> None:
    from pathlib import Path  # noqa: PLC0415

    from odb_processing.sinesp import load_coverage  # noqa: PLC0415

    path = Path(__file__).parents[3] / "configs" / "sources" / "coverage" / "sinesp_vde.toml"
    entries, sha = load_coverage(path)
    assert len(sha) == 64
    assert entries
    assert {e for entry in entries for e in entry.events} <= EVENTS
    assert all(entry.uf in {"TO", "MT", "BA", "CE", "AL", "RS"} for entry in entries)


def test_coverage_marks_state_rows_unavailable(tmp_path: object) -> None:
    from odb_processing.sinesp import Unavailable  # noqa: PLC0415

    gap = Unavailable("SP", ("Homicídio doloso", "Furto de veículo"), "202301", "202312", "teste")
    out, report = sinesp_observations(
        RAW,
        year="2023",
        uf_codes=UF_CODES,
        municipalities=MUNICIPALITIES,
        table_id="SINESP-VDE-2023",
        lineage=LINEAGE,
        unavailable=[gap, Unavailable("AC", ("Evento inexistente",), "202301", "202301", "x")],
    )
    # Zero publicado no município vira "não disponível"; a UF também.
    assert _value(out, "homicidio-doloso", "6", "3545803", "Sexo=T")[1] == "not_available"
    assert _value(out, "homicidio-doloso", "3", "35", "Sexo=T")[1] == "not_available"
    # Brasil com UF indisponível também fica indisponível (nunca um total parcial).
    assert _value(out, "homicidio-doloso", "1", "1", "Sexo=T")[1] == "not_available"
    # Outra UF não muda.
    assert _value(out, "homicidio-doloso", "6", "1200401", "Sexo=T")[0] == 5
    # A parte federal (PF) não é afetada pela cobertura estadual.
    assert _value(out, "furto-de-veiculo", "3", "35", "Abrangência=policia-federal")[0] == 2
    assert report.coverage_applied == {"SP 202301-202312: Homicídio doloso, Furto de veículo": 3}
    assert report.coverage_unknown_events == ["Evento inexistente"]
