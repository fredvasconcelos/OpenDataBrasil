"""Funções puras da Silver das contas públicas (ADR-0030 a 0035)."""

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl
import pytest

from odb_processing.contas import (
    decimal_value,
    municipality_names,
    name_key,
    parse_tabmun,
    period_from_raw,
    read_source_csv,
    recipient_class,
    resolve_by_name,
    resolve_by_siafi,
    territory_corrections,
)
from odb_processing.parsers import Lineage, ParseError

LINEAGE = Lineage("art", "sha", "https://x", datetime.now(UTC), "ing", "run", datetime.now(UTC))
COLUMNS = (("Código", "code"), ("Nome", "name"), ("Valor", "value_raw"))
TABMUN = (
    "2033;08785479000120;GUARABIRA                                    ;PB;2506301\r\n"
    "1625;08085524000100;CAMPO GRANDE (EX-AUGUSTO SEVERO)             ;RN;2401305\r\n"
    "1805;08085516000163;SERRA CAIADA (EX-PRESIDENTE JUSCELINO)       ;RN;2410306\r\n"
).encode("latin-1")
DTB = pl.DataFrame(
    {
        "municipality_id": ["2506301", "2401305", "2410306", "2701506", "5101837"],
        "municipality_name": [
            "Guarabira",
            "Campo Grande",
            "Serra Caiada",
            "Campo Grande",
            "Boa Esperança do Norte",
        ],
        "uf_id": ["25", "24", "24", "27", "51"],
    }
)


def _tabmun() -> pl.DataFrame:
    return parse_tabmun(TABMUN, LINEAGE, "tesouro-tabmun").frame


def test_read_source_csv_counts_records_and_keeps_text() -> None:
    content = (
        '"Código";"Nome";"Valor"\r\n"1";"ÓRGÃO \'\'A\'\'";"10,50"\r\n"2";"linha\r\nquebrada";""\r\n'
    ).encode("latin-1")
    table = read_source_csv(content, COLUMNS, encoding="latin-1")
    assert table.records == 2  # a quebra de linha entre aspas não é registro
    assert table.frame.height == 2
    assert table.frame["line_number"].to_list() == [1, 2]
    assert table.frame["name"][0] == "ÓRGÃO ''A''"
    assert table.frame.schema["value_raw"] == pl.String
    with pytest.raises(ParseError, match="cabeçalho difere"):
        read_source_csv(b'"Codigo";"Nome";"Valor"\r\n', COLUMNS, encoding="latin-1")


def test_decimal_accepts_missing_leading_zero_and_rejects_garbage() -> None:
    raw = ["411015629,21", ",8500", "-,85", "-1234,5", "3328", "1.234,56", "abc", ""]
    out = pl.DataFrame({"v": raw}).select(decimal_value("v")).to_series().to_list()
    assert out[:5] == [
        Decimal("411015629.21"),
        Decimal("0.85"),
        Decimal("-0.85"),
        Decimal("-1234.5"),
        Decimal("3328"),
    ]
    assert out[5:] == [None, None, None]  # milhar com ponto não existe na fonte: erro, não 0


def test_name_key_and_period_formats() -> None:
    frame = pl.DataFrame({"n": ["São João d\u2019Aliança", "SAO JOAO D'ALIANCA", " Itapagé "]})
    assert frame.select(name_key("n")).to_series().to_list() == [
        "SAO JOAO D ALIANCA",
        "SAO JOAO D ALIANCA",
        "ITAPAGE",
    ]
    raw = pl.DataFrame({"a": ["202510"], "b": ["10/2025"], "c": ["2025/10"]})
    assert raw.select(
        period_from_raw("a", "aaaamm"),
        period_from_raw("b", "mm/aaaa"),
        period_from_raw("c", "aaaa/mm"),
    ).row(0) == ("202510", "202510", "202510")


def test_tabmun_keeps_former_official_names() -> None:
    frame = _tabmun()
    rn = frame.filter(pl.col("uf") == "RN").sort("siafi_code")
    assert rn["current_name"].to_list() == ["CAMPO GRANDE", "SERRA CAIADA"]
    assert rn["former_name"].to_list() == ["AUGUSTO SEVERO", "PRESIDENTE JUSCELINO"]
    assert frame.filter(pl.col("uf") == "PB")["former_name"].to_list() == [None]


def test_municipality_names_refuses_ambiguity() -> None:
    names = municipality_names(DTB, _tabmun())
    rn = names.filter((pl.col("uf") == "RN") & (pl.col("name_key") == "PRESIDENTE JUSCELINO"))
    assert rn.rows() == [("RN", "PRESIDENTE JUSCELINO", "2410306", "nome_antigo_tabmun")]
    # "Campo Grande" existe em RN e AL: nomes repetidos só em UFs diferentes.
    assert names.filter(pl.col("name_key") == "CAMPO GRANDE").height == 2
    clash = pl.concat([DTB, pl.DataFrame({"municipality_id": ["2599999"],
                                          "municipality_name": ["Guarabira"],
                                          "uf_id": ["25"]})])  # fmt: skip
    with pytest.raises(ParseError, match="ambíguos"):
        municipality_names(clash, _tabmun())


def test_resolve_by_siafi_and_by_name() -> None:
    tabmun = _tabmun()
    names = municipality_names(DTB, tabmun)
    lens_a = pl.DataFrame(
        {
            "uf": ["PB", "PB", "MT", "MU", "PB"],
            "siafi_municipality_code": ["2033", None, "1182", "-14", "9999"],
            "municipality_name_source": [
                "GUARABIRA",
                None,
                "BOA ESPERANCA DO NORTE",
                "Múltiplo",
                "X",
            ],
        }
    )
    out = resolve_by_siafi(lens_a, tabmun, names)
    assert out.select("municipality_id", "territory_status", "territory_method").rows() == [
        ("2506301", "municipio", "tabmun_siafi"),
        (None, "sem_municipio", None),
        ("5101837", "municipio", "nome_uf_dtb"),  # município novo, fora da TABMUN de 2021
        (None, "multiplo", None),
        (None, "nao_resolvido", None),
    ]
    lens_b = pl.DataFrame(
        {
            "uf": ["RN", "EX", "-1", "PB", "PB"],
            "municipality_name_source": [
                "PRESIDENTE JUSCELINO",
                "Exterior",
                "Sem informação",
                "GUARABIRA",
                "INEXISTENTE",
            ],
        }
    )
    out = resolve_by_name(lens_b, names)
    assert out.select("municipality_id", "territory_status", "territory_method").rows() == [
        ("2410306", "municipio", "nome_antigo_tabmun"),
        (None, "exterior", None),
        (None, "sem_informacao", None),
        ("2506301", "municipio", "nome_uf_dtb"),
        (None, "nao_resolvido", None),
    ]


# Caso real: o SIAFI 4196 "CACHOEIRA DO PAJEU"/MG é o FPM de Boa Esperança do Norte/MT
# (5101837), pelo valor igual ao centavo no Tesouro (ADR-0038). O destino pode ser de outra
# UF: o município manda na UF da linha.
PAJEU = {
    "uf": "MG",
    "siafi_code": "4196",
    "source_name": "CACHOEIRA DO PAJEU",
    "municipality_id": "5101837",
    "reason": "valor igual ao centavo no FPM de Boa Esperança do Norte no Tesouro",
    "approved": "2026-11-22, mantenedor",
}


def test_approved_correction_matches_only_the_exact_key() -> None:
    """Correção confirmada: casa por UF + SIAFI + nome exatos, nunca por semelhança."""
    tabmun = _tabmun()
    names = municipality_names(DTB, tabmun)
    wrong_guarabira = {**PAJEU, "uf": "PB", "siafi_code": "2033", "source_name": "GUARABIRA"}
    fixes = territory_corrections([PAJEU, wrong_guarabira], ["5101837", "2506301"])
    lens_a = pl.DataFrame(
        {
            "uf": ["MG", "MG", "MG", "SP", "PB"],
            "siafi_municipality_code": ["4196", "4196", "4197", "4196", "2033"],
            "municipality_name_source": [
                "Cachoeira do Pajeú",  # mesma chave depois da normalização
                "CACHOEIRA DO PAJEUS",
                "CACHOEIRA DO PAJEU",
                "CACHOEIRA DO PAJEU",
                "GUARABIRA",
            ],
        }
    )
    out = resolve_by_siafi(lens_a, tabmun, names, fixes)
    assert out.select("municipality_id", "territory_status", "territory_method").rows() == [
        ("5101837", "municipio", "correcao_aprovada"),
        (None, "nao_resolvido", None),  # outro nome
        (None, "nao_resolvido", None),  # outro SIAFI
        (None, "nao_resolvido", None),  # outra UF
        ("2506301", "municipio", "tabmun_siafi"),  # o SIAFI oficial vence a correção
    ]


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        ([{**PAJEU, "reason": ""}], "sem"),
        ([{k: v for k, v in PAJEU.items() if k != "approved"}], "sem"),
        ([{**PAJEU, "municipality_id": "9999999"}], "fora da DTB"),
        ([PAJEU, {**PAJEU, "source_name": "Cachoeira do Pajeú"}], "repetidas"),
    ],
)
def test_corrections_are_validated(entries: list[dict[str, str]], message: str) -> None:
    with pytest.raises(ParseError, match=message):
        territory_corrections(entries, ["5101837"])


@pytest.mark.parametrize(
    ("code", "nature", "cnae", "prefecture", "expected"),
    [
        ("RB0000003", None, None, False, "lancamento_agregado"),
        ("TN0000001", None, None, False, "lancamento_agregado"),
        ("170500", None, None, False, "unidade_gestora_federal"),
        ("-11", None, None, False, "sigiloso"),
        ("-1", None, None, False, "sem_informacao"),
        ("-3", None, None, False, "sem_informacao"),
        ("-8", None, None, False, "sem_informacao"),
        ("-9", None, None, False, "sem_informacao"),
        ("EX1134806", None, None, False, "exterior"),
        ("***.810.079-**", None, None, False, "pessoa_fisica"),
        ("PFAUXPESQ", None, None, False, "pessoa_fisica_sem_cpf"),
        ("08785479000120", "1244", None, True, "municipio"),
        ("08785479000120", "1031", None, True, "municipio"),  # CNPJ da prefeitura na TABMUN
        ("08761124000100", "1236", None, False, "estado_df"),
        ("19184104000121", "1333", None, False, "fundo_municipal"),
        ("01234567000189", "1325", None, False, "fundo_estadual"),
        ("00000000000191", "2038", "6422100", False, "instituicao_financeira"),
        ("50875450000104", "2062", "4789099", False, "empresa"),
        ("07157660000120", "3999", "9493600", False, "entidade_sem_fins_lucrativos"),
        ("11111111000111", "4120", None, False, "pessoa_fisica_com_cnpj"),
        ("22222222000122", "0000", "00000", False, "nao_classificado"),
    ],
)
def test_recipient_class(
    code: str, nature: str | None, cnae: str | None, prefecture: bool, expected: str
) -> None:
    frame = pl.DataFrame(
        {
            "recipient_code": [code],
            "legal_nature_code": [nature],
            "cnae_code": [cnae],
            "is_prefecture": [prefecture],
        },
        schema={
            "recipient_code": pl.String,
            "legal_nature_code": pl.String,
            "cnae_code": pl.String,
            "is_prefecture": pl.Boolean,
        },
    )
    assert frame.select(recipient_class()).item() == expected
