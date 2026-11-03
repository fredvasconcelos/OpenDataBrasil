import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from odb_ingestion import ConfigError, HttpClient, HttpError, load_sources
from odb_ingestion.config import DatasetConfig, HttpPolicy
from odb_ingestion.connectors.sidra import SidraConnector
from odb_ingestion.contract import ExtractionRequest, PartitionState, Watermark
from odb_ingestion.http import DownloadResult
from tests.ingestion_support import SIDRA_FIXTURES, TEST_SOURCES, FakeSources

PERIODS_6579 = [
    "2001",
    "2002",
    "2003",
    "2004",
    "2005",
    "2006",
    "2008",
    "2009",
    "2011",
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
    "2021",
    "2024",
    "2025",
    "2026",
]


@pytest.fixture
def connector() -> SidraConnector:
    catalog = load_sources(TEST_SOURCES)
    return SidraConnector(catalog.sources["ibge-sidra"], catalog.datasets_of("ibge-sidra"))


@pytest.fixture
def fake() -> FakeSources:
    return FakeSources()


@pytest.fixture
def http(fake: FakeSources) -> HttpClient:
    return HttpClient(HttpPolicy(min_interval_s=0, max_attempts=1), transport=fake.transport())


def _result(path: Path) -> DownloadResult:
    return DownloadResult(
        "u", 200, {}, datetime.now(UTC), path=path, size_bytes=path.stat().st_size, sha256="x"
    )


def _request(period: str) -> ExtractionRequest:
    return ExtractionRequest(f"n1n2n3-p{period}", "u", "a.json", reference_period=period)


def test_discover_periods_from_real_fixture(connector: SidraConnector, http: HttpClient) -> None:
    dataset = connector.describe("ibge-sidra-6579")
    assert connector.discover_periods(dataset, http) == PERIODS_6579


def test_plan_full_incremental_and_refresh(connector: SidraConnector, http: HttpClient) -> None:
    plan = connector.plan("ibge-sidra-6579", http, Watermark())
    assert [r.reference_period for r in plan.requests] == PERIODS_6579
    first = plan.requests[0]
    assert (
        first.url == "https://apisidra.ibge.gov.br/values/t/6579/n1/all/n2/all/n3/all/v/9324/p/2001"
    )
    assert first.artifact_name == "t6579-n1n2n3-p2001.json"
    assert first.partition_key == "n1n2n3-p2001"

    known = Watermark({f"n1n2n3-p{p}": PartitionState(checksum_sha256="x") for p in PERIODS_6579})
    incremental = connector.plan("ibge-sidra-6579", http, known)
    assert [r.reference_period for r in incremental.requests] == ["2025", "2026"]
    assert any("fora da janela" in n for n in incremental.notes)
    assert incremental.metadata["refresh_recent_periods"] == ["2025", "2026"]
    assert len(connector.plan("ibge-sidra-6579", http, known, full=True).requests) == 22

    multi = connector.plan("ibge-sidra-4714", http, Watermark())
    assert [r.url for r in multi.requests] == [
        "https://apisidra.ibge.gov.br/values/t/4714/n1/all/n2/all/n3/all/v/93,6318,614/p/2022"
    ]


def test_real_fixtures_validate(connector: SidraConnector) -> None:
    result = connector.validate_raw(
        "ibge-sidra-6579", _request("2025"), _result(SIDRA_FIXTURES / "t6579_n1n2n3_p2025.json")
    )
    assert result.valid, result.errors
    assert result.stats["observations"] == 33
    assert result.stats["territories"] == 33  # (nível, código): Brasil=1 e Norte=1 são distintos
    assert result.stats["levels"] == {"1": 1, "2": 5, "3": 27}
    assert result.stats["units"] == ["Pessoas"]
    census = connector.validate_raw(
        "ibge-sidra-4714", _request("2022"), _result(SIDRA_FIXTURES / "t4714_n1n2n3_p2022.json")
    )
    assert census.valid, census.errors
    assert census.stats["variables"] == ["614", "6318", "93"]


def test_empty_period_response_is_invalid(connector: SidraConnector) -> None:
    """Comportamento real: período inexistente → HTTP 200 só com cabeçalho."""
    result = connector.validate_raw(
        "ibge-sidra-6579", _request("1900"), _result(SIDRA_FIXTURES / "t6579_n3_p1900_empty.json")
    )
    assert not result.valid
    assert "sem observações" in result.errors[0]


def _mutated(tmp_path: Path, mutate: object) -> Path:
    payload = json.loads((SIDRA_FIXTURES / "t6579_n1n2n3_p2025.json").read_text("utf-8"))
    mutate(payload)  # type: ignore[operator]
    path = tmp_path / "m.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.__setitem__(slice(2, None), []), "observações, mínimo"),
        (lambda p: p.append(dict(p[1])), "máximo esperado"),
        (lambda p: [r.__setitem__("NC", "3") for r in p[1:]], "níveis territoriais"),
        (lambda p: p[1].__setitem__("D3C", "2024"), "períodos inesperados"),
        (lambda p: p[1].__setitem__("D2C", "93"), "variáveis"),
        (lambda p: p.__setitem__(2, dict(p[1])), "duplicadas"),
        (lambda p: p[1].pop("V"), "colunas diferentes"),
        (lambda p: p[0].pop("D3C"), "cabeçalho sem"),
    ],
)
def test_structural_errors(
    connector: SidraConnector, tmp_path: Path, mutate: object, message: str
) -> None:
    result = connector.validate_raw(
        "ibge-sidra-6579", _request("2025"), _result(_mutated(tmp_path, mutate))
    )
    assert not result.valid
    assert any(message in e for e in result.errors), result.errors


def test_special_values_counted_and_unknown_warned(
    connector: SidraConnector, tmp_path: Path
) -> None:
    def mutate(p: list[dict[str, str]]) -> None:
        p[1]["V"] = "..."
        p[2]["V"] = "X"
        p[3]["V"] = "?"

    result = connector.validate_raw(
        "ibge-sidra-6579", _request("2025"), _result(_mutated(tmp_path, mutate))
    )
    assert result.valid
    assert result.stats["special_values"] == {"...": 1, "X": 1, "?": 1}
    assert any("não catalogados" in w for w in result.warnings)


def test_non_json_and_wrong_shape(connector: SidraConnector, tmp_path: Path) -> None:
    bad = tmp_path / "b.json"
    bad.write_text("<html>erro</html>")
    assert (
        "JSON inválido"
        in connector.validate_raw("ibge-sidra-6579", _request("2025"), _result(bad)).errors[0]
    )
    bad.write_text('{"a": 1}')
    assert (
        "formato inesperado"
        in connector.validate_raw("ibge-sidra-6579", _request("2025"), _result(bad)).errors[0]
    )
    empty = DownloadResult("u", 304, {}, datetime.now(UTC))
    assert connector.validate_raw("ibge-sidra-6579", _request("2025"), empty).errors


def test_params_validation(connector: SidraConnector) -> None:
    base = connector.describe("ibge-sidra-6579")

    def with_params(**changes: object) -> DatasetConfig:
        return base.model_copy(update={"params": {**base.params, **changes}})

    for bad in (
        {"table": "abc"},
        {"variables": ["x"]},
        {"territorial_level": "zz"},
        {"period_dimension": "X1"},
        {"classifications": {"c2": "a,b"}},
        {"unknown_param": 1},
    ):
        with pytest.raises(ConfigError, match="parâmetros SIDRA"):
            connector.validate_params(with_params(**bad))
    with pytest.raises(ConfigError, match="limite do SIDRA"):
        connector.validate_params(with_params(estimated_values_per_period=100_001))
    ok = with_params(classifications={"c2": "all", "c1": "1,2"})
    connector.validate_params(ok)
    url = connector._values_url(connector.params(ok), ("n3",), "9324", "2025")
    assert url.endswith("/p/2025/c1/1,2/c2/all")


def test_discovery_failures(connector: SidraConnector, fake: FakeSources, http: HttpClient) -> None:
    dataset = connector.describe("ibge-sidra-6579")
    path = "/values/t/6579/n1/all/v/9324/p/all"
    cases = [(b"<html>", "não é JSON"), (b"[{}]", "nenhum período"), (b'[{}, {"x": 1}]', "ausente")]
    for body, message in cases:

        def respond(_r: httpx.Request, content: bytes = body) -> httpx.Response:
            return httpx.Response(200, content=content)

        fake.overrides[path] = respond
        with pytest.raises(HttpError, match=message):
            connector.discover_periods(dataset, http)


def test_healthcheck(connector: SidraConnector, fake: FakeSources, http: HttpClient) -> None:
    assert connector.healthcheck(http).ok
    fake.overrides["/values/t/6579/n1/all/v/9324/p/last"] = lambda _r: httpx.Response(503)
    status = connector.healthcheck(http)
    assert not status.ok
    assert "503" in status.detail
    empty = SidraConnector(connector.source, [])
    assert not empty.healthcheck(http).ok
    with pytest.raises(KeyError, match="não pertence"):
        empty.describe("ibge-sidra-6579")
