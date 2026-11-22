"""Silver das contas públicas, da Bronze à Delta, com a configuração real (ADR-0030 a 0035).

O servidor simulado gera os ZIPs da CGU e a TABMUN com os cabeçalhos reais; a DTB é a
fixture real de 2025. O intervalo das lentes é reduzido a dois meses.
"""

import io
import re
import tomllib
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import polars as pl
import pytest

from odb_common.storage import LakehouseLayout
from odb_ingestion import BronzeStore, HttpClient, IngestionRunner, build_connectors, load_sources
from odb_ingestion.config import SourceCatalog, SourcesFile
from odb_ingestion.contract import BaseConnector
from odb_lakehouse import DeltaReader, DeltaWriter, InProcessLock
from odb_processing.contas_layout import (
    CNAE_COLUMNS,
    EXECUTION_COLUMNS,
    LEGAL_ENTITY_COLUMNS,
    NATURE_COLUMNS,
    PAYMENT_COLUMNS,
    TRANSFER_COLUMNS,
)
from odb_processing.silver import SilverBuilder
from tests.ingestion_support import TEST_SOURCES, FakeSources, InMemoryRegistry
from tests.silver_support import InMemorySilverRegistry

REPO_SOURCES = Path(__file__).parents[3] / "configs" / "sources"
LENSES = ("cgu-transferencias", "cgu-despesas-favorecidos", "cgu-despesas-execucao")
ALL = (
    "ibge-dtb",
    "tesouro-tabmun",
    "cgu-favorecidos-pj",
    *LENSES,
)
TABMUN = (
    "2033;08785479000120;GUARABIRA                                    ;PB;2506301\r\n"
    "1805;08085516000163;SERRA CAIADA (EX-PRESIDENTE JUSCELINO)       ;RN;2410306\r\n"
).encode("latin-1")


def _line(values: list[str]) -> str:
    return ";".join(f'"{v}"' for v in values)


def _csv(columns: tuple[tuple[str, str], ...], rows: list[dict[str, str]]) -> bytes:
    lines = [_line([h for h, _ in columns])]
    lines += [_line([row.get(name, "") for _, name in columns]) for row in rows]
    return ("\r\n".join(lines) + "\r\n").encode("latin-1")


def _zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buf.getvalue()


def _transfer_rows(period: str, extra: str = "") -> list[dict[str, str]]:
    fpm = {
        "period_raw": period,
        "transfer_type": "Constitucionais e Royalties",
        "recipient_type": "Administração Pública Municipal",
        "uf": "PB",
        "siafi_municipality_code": "2033",
        "municipality_name_source": "GUARABIRA",
        "organ_code": "-1",
        "action_code": "0045",
        "action_name": "TRANSFERENCIA AO FUNDO DE PARTICIPACAO DOS MUNICIPIOS - FPM",
        "recipient_code": "08785479000120",
        "recipient_name": "MUNICIPIO DE GUARABIRA",
        "value_raw": "1000,50",
    }
    state = {
        **fpm,
        "recipient_type": "Administração Pública Estadual ou do Distrito Federal",
        "siafi_municipality_code": "",
        "municipality_name_source": "",
        "recipient_code": "08761124000100",
        "recipient_name": "ESTADO DA PARAIBA",
        "value_raw": ",85",
    }
    new_municipality = {
        **fpm,
        "uf": "MT",
        "siafi_municipality_code": "1182",
        "municipality_name_source": "BOA ESPERANCA DO NORTE" + extra,
        "recipient_code": "33333333000133",
        "recipient_name": "FUNDO MUNICIPAL DE SAUDE",
        "value_raw": "-12,00",
    }
    return [fpm, dict(fpm), state, new_municipality]  # fpm repetido: linha idêntica legítima


def _payment_rows(period: str) -> list[dict[str, str]]:
    month = f"{period[4:]}/{period[:4]}"
    base = {
        "superior_organ_code": "26000",
        "organ_code": "26298",
        "management_unit_code": "153173",
        "period_raw": month,
    }
    return [
        {**base, "recipient_code": "***.810.079-**", "recipient_name": "FULANA DE TAL",
         "uf": "RN", "municipality_name_source": "PRESIDENTE JUSCELINO", "value_raw": "700"},
        {**base, "recipient_code": "50875450000104", "recipient_name": "ATLAS LTDA",
         "uf": "PB", "municipality_name_source": "GUARABIRA", "value_raw": "356964,30"},
        {**base, "recipient_code": "EX1134806", "recipient_name": "",
         "uf": "EX", "municipality_name_source": "Exterior", "value_raw": "469068,7300"},
        {**base, "recipient_code": "-11", "recipient_name": "Sigiloso",
         "uf": "-1", "municipality_name_source": "Sem informação", "value_raw": "10"},
        {**base, "recipient_code": "00000000000191", "recipient_name": "BANCO DO BRASIL SA",
         "uf": "DF", "municipality_name_source": "BRASÍLIA", "value_raw": "15,20"},
    ]  # fmt: skip


def _execution_rows(period: str) -> list[dict[str, str]]:
    return [
        {
            "period_raw": f"{period[:4]}/{period[4:]}",
            "management_unit_code": "167399",
            "action_code": "2004",
            "committed_raw": "805942,86",
            "liquidated_raw": "698956,52",
            "paid_raw": "743598,53",
            "payables_registered_raw": "0,00",
            "payables_cancelled_raw": "0,00",
            "payables_paid_raw": "27426,73",
        }
    ]


def _pj_zip(period: str) -> bytes:
    entities = [
        {"recipient_code": "08785479000120", "company_name": "MUNICIPIO DE GUARABIRA",
         "cnae_code": "8411600", "legal_nature_code": "1244"},
        {"recipient_code": "08761124000100", "company_name": "ESTADO DA PARAIBA",
         "cnae_code": "8411600", "legal_nature_code": "1236"},
        {"recipient_code": "33333333000133", "company_name": "FUNDO MUNICIPAL DE SAUDE",
         "cnae_code": "8411600", "legal_nature_code": "1333"},
        {"recipient_code": "50875450000104", "company_name": "ATLAS LTDA",
         "cnae_code": "4789099", "legal_nature_code": "2062"},
        {"recipient_code": "00000000000191", "company_name": "BANCO DO BRASIL SA",
         "cnae_code": "6422100", "legal_nature_code": "2038"},
    ]  # fmt: skip
    cnae = [
        {"cnae_section_code": "O", "cnae_section_description": "ADMINISTRAÇÃO PÚBLICA",
         "cnae_code": "8411600", "cnae_description": "Administração pública em geral"},
        {"cnae_section_code": "K", "cnae_section_description": "ATIVIDADES FINANCEIRAS",
         "cnae_code": "6422100", "cnae_description": "Bancos múltiplos, com carteira comercial"},
    ]  # fmt: skip
    natures = [
        {"legal_nature_code": c, "legal_nature_description": d, "legal_nature_type_code": c[0]}
        for c, d in (("1244", "Município"), ("1236", "Estado ou Distrito Federal"),
                     ("1333", "Fundo Público da Administração Direta Municipal"),
                     ("2062", "Sociedade Empresária Limitada"),
                     ("2038", "Sociedade de Economia Mista"))
    ]  # fmt: skip
    return _zip(
        {
            f"{period}_CNPJ.csv": _csv(LEGAL_ENTITY_COLUMNS, entities),
            f"{period}_CNAE.csv": _csv(CNAE_COLUMNS, cnae),
            f"{period}_NaturezaJuridica.csv": _csv(NATURE_COLUMNS, natures),
        }
    )


_PATH = re.compile(r"/saida/(?P<base>[a-z-]+)/(?P<period>\d{6})_(?P<name>\w+)\.zip$")


@dataclass
class FakePortal:
    """Bucket da CGU e CKAN do Tesouro simulados; o resto vai para o IBGE simulado."""

    ibge: FakeSources = field(default_factory=FakeSources)
    transfer_suffix: dict[str, str] = field(default_factory=dict)
    version: dict[str, int] = field(default_factory=dict)

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.tesourotransparente.gov.br":
            return httpx.Response(200, content=TABMUN, headers={"etag": '"tabmun"'})
        if request.url.host != "dadosabertos-download.cgu.gov.br":
            return self.ibge.handler(request)
        match = _PATH.search(request.url.path)
        if match is None:
            return httpx.Response(403, content=b"<Error><Code>AccessDenied</Code></Error>")
        base, period = match["base"], match["period"]
        if request.headers.get("range"):
            return httpx.Response(206, content=b"P")
        content = {
            "transferencias": lambda: _zip(
                {
                    f"{period}_Transferencias.csv": _csv(
                        TRANSFER_COLUMNS,
                        _transfer_rows(period, self.transfer_suffix.get(period, "")),
                    )
                }
            ),
            "despesas-favorecidos": lambda: _zip(
                {
                    f"{period}_RecebimentosRecursosPorFavorecido.csv": _csv(
                        PAYMENT_COLUMNS, _payment_rows(period)
                    )
                }
            ),
            "despesas-execucao": lambda: _zip(
                {f"{period}_Despesas.csv": _csv(EXECUTION_COLUMNS, _execution_rows(period))}
            ),
            "favorecidos-pj": lambda: _pj_zip(period),
        }[base]()
        return httpx.Response(200, content=content, headers={"content-type": "application/zip"})


def _catalog(max_unresolved: int | None = None) -> SourceCatalog:
    """Fontes de teste do IBGE + cgu.toml e tesouro.toml reais, com dois meses por lente."""
    files = list(load_sources(TEST_SOURCES).files)
    for name in ("cgu.toml", "tesouro.toml"):
        data: dict[str, Any] = tomllib.loads((REPO_SOURCES / name).read_text("utf-8"))
        for dataset in data["datasets"]:
            if dataset["id"] in LENSES:
                dataset["params"]["start"], dataset["params"]["end"] = "202410", "202411"
                if max_unresolved is not None and "max_unresolved_territory" in dataset["silver"]:
                    dataset["silver"]["max_unresolved_territory"] = max_unresolved
            dataset["params"].pop("min_bytes", None)  # os arquivos simulados são pequenos
        files.append(SourcesFile.model_validate(data))
    return SourceCatalog(files)


class Env:
    def __init__(self, tmp_path: Path, max_unresolved: int | None = None) -> None:
        self.catalog = _catalog(max_unresolved)
        self.layout = LakehouseLayout((tmp_path / "lake").as_uri())
        self.portal = FakePortal()
        self.ingestion = InMemoryRegistry()

        def factory(connector: BaseConnector) -> HttpClient:
            return HttpClient(
                connector.source.http,
                transport=httpx.MockTransport(self.portal.handler),
                sleep=lambda _s: None,
            )

        self.runner = IngestionRunner(
            self.catalog,
            build_connectors(self.catalog),
            BronzeStore(self.layout),
            self.ingestion,
            factory,
        )
        self.registry = InMemorySilverRegistry(self.ingestion)
        self.builder = SilverBuilder(
            self.catalog,
            self.layout,
            DeltaWriter(self.layout, InProcessLock()),
            self.registry,
            code_version="test",
        )

    def ingest(self, *datasets: str) -> None:
        for d in datasets:
            report = self.runner.run(d)
            assert report.status == "succeeded", report.error

    def table(self, dataset_id: str) -> pl.DataFrame:
        uri = self.builder.target_uri(self.catalog.dataset(dataset_id))
        reader = DeltaReader()
        return reader.scan(uri, reader.current_version(uri)).collect()


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def _checks(env: Env, run_id: str) -> dict[str, Any]:
    return {c.check_id: c for c in env.registry.checks[run_id]}


def test_lenses_build_after_references_with_territory_and_class(env: Env) -> None:
    env.ingest(*ALL)
    runs = env.builder.build_many(list(reversed(ALL)))
    order = [r.dataset_id for r in runs]
    for lens in ("cgu-transferencias", "cgu-despesas-favorecidos"):
        for ref in ("ibge-dtb", "tesouro-tabmun", "cgu-favorecidos-pj"):
            assert order.index(ref) < order.index(lens)
    assert all(r.status == "succeeded" for r in runs), [(r.dataset_id, r.error) for r in runs]

    transfer = env.table("cgu-transferencias").sort("period", "line_number")
    assert transfer.height == 8  # 4 por mês, nenhuma linha removida
    october = transfer.filter(pl.col("period") == "202410")
    assert october.select("municipality_id", "territory_status", "territory_method",
                          "recipient_class").rows() == [
        ("2506301", "municipio", "tabmun_siafi", "municipio"),
        ("2506301", "municipio", "tabmun_siafi", "municipio"),
        (None, "sem_municipio", None, "estado_df"),
        ("5101837", "municipio", "nome_uf_dtb", "fundo_municipal"),
    ]  # fmt: skip
    assert october["value"].to_list() == [
        Decimal("1000.50"),
        Decimal("1000.50"),
        Decimal("0.85"),
        Decimal("-12.00"),
    ]
    assert october["value_raw"].to_list() == ["1000,50", "1000,50", ",85", "-12,00"]
    assert october["derivation_refs"].unique().to_list()[0].startswith("ibge-dtb@v")
    run = next(r for r in runs if r.dataset_id == "cgu-transferencias")
    checks = _checks(env, run.run_id)
    assert checks["rows.identical_preserved"].observed == 1
    assert checks["incremental.months"].observed == 2

    payment = env.table("cgu-despesas-favorecidos").filter(pl.col("period") == "202411")
    assert payment.select("recipient_class", "territory_status", "municipality_id").rows() == [
        ("pessoa_fisica", "municipio", "2410306"),  # nome antigo oficial (TABMUN)
        ("empresa", "municipio", "2506301"),
        ("exterior", "exterior", None),
        ("sigiloso", "sem_informacao", None),
        ("instituicao_financeira", "municipio", "5300108"),
    ]
    assert payment["recipient_name"][0] == "FULANA DE TAL"  # PF publicada como na fonte
    execution = env.table("cgu-despesas-execucao")
    assert execution["paid"].to_list() == [Decimal("743598.53")] * 2


def test_only_changed_months_are_rebuilt(env: Env) -> None:
    env.ingest(*ALL)
    env.builder.build_many(list(ALL))
    # Sem mudança: o build é pulado (mesma impressão digital), sem versão Delta nova.
    again = env.builder.build("cgu-transferencias")
    assert again.status == "skipped"
    # A fonte revisa novembro: só ele é relido e substituído.
    env.portal.transfer_suffix["202411"] = " "  # espaço extra: bytes novos, mesmo município
    env.ingest("cgu-transferencias")
    run = env.builder.build("cgu-transferencias")
    assert run.status == "succeeded", run.error
    months = _checks(env, run.run_id)["incremental.months"]
    assert months.details["meses"] == ["202411"]
    transfer = env.table("cgu-transferencias")
    assert transfer.height == 8
    by_month = dict(transfer.group_by("period").agg(pl.col("silver_run_id").first()).iter_rows())
    assert by_month["202411"] == run.run_id
    assert by_month["202410"] != run.run_id  # outubro ficou como estava


def test_unresolved_municipality_stays_in_uf_below_the_limit(env: Env) -> None:
    """Até o teto da configuração (10 por mês), a linha fica na UF, com aviso."""
    env.portal.transfer_suffix["202410"] = " DO SUL"  # nome que não existe na UF
    env.ingest(*ALL)
    runs = env.builder.build_many(list(ALL))
    transfer = next(r for r in runs if r.dataset_id == "cgu-transferencias")
    assert transfer.status == "succeeded", transfer.error
    assert _checks(env, transfer.run_id)["territory.resolved"].status.value == "warn"
    row = env.table("cgu-transferencias").filter(pl.col("territory_status") == "nao_resolvido")
    assert row.select("uf", "municipality_id", "value_raw").rows() == [("MT", None, "-12,00")]


def test_unresolved_municipality_above_the_limit_blocks_the_write(tmp_path: Path) -> None:
    env = Env(tmp_path, max_unresolved=0)
    env.portal.transfer_suffix["202410"] = " DO SUL"
    env.ingest(*ALL)
    runs = env.builder.build_many(list(ALL))
    transfer = next(r for r in runs if r.dataset_id == "cgu-transferencias")
    assert transfer.status == "failed"
    assert "territory.resolved" in (transfer.error or "")
    uri = env.builder.target_uri(env.catalog.dataset("cgu-transferencias"))
    assert not Path(uri.removeprefix("file://")).exists()  # nada gravado
