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

REPO_SOURCES = Path(__file__).parents[3] / "configs" / "sources"

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


def test_split_by_variable_and_category(connector: SidraConnector, http: HttpClient) -> None:
    plan = connector.plan("ibge-sidra-9718", http, Watermark())
    keys = [r.partition_key for r in plan.requests]
    assert len(keys) == 9
    assert keys[:3] == [
        "n1n2n3-p2022-v93-c2661-32776",
        "n1n2n3-p2022-v93-c2661-12869",
        "n1n2n3-p2022-v93-c2661-12870",
    ]
    request = plan.requests[4]
    assert request.partition_key == "n1n2n3-p2022-v350-c2661-12869"
    assert request.url == (
        "https://apisidra.ibge.gov.br/values/t/9718/n1/all/n2/all/n3/all/v/350/p/2022"
        "/c1714/all/c2661/12869"
    )
    assert request.artifact_name == "t9718-n1n2n3-p2022-v350-c2661-12869.json"
    params = connector.params(connector.describe("ibge-sidra-9718"))
    assert params.request_variables("n1n2n3-p2022-v350-c2661-12869") == ("350",)
    assert params.partition_pattern().fullmatch("n1n2n3-p2022-v350") is None
    with pytest.raises(ValueError, match="fora da configuração"):
        params.request_variables("n1n2n3-p2022")
    with pytest.raises(ValueError, match="exige o grupo"):
        params.partition_key("2022")

    ok = connector.validate_raw(
        "ibge-sidra-9718",
        request,
        _result(SIDRA_FIXTURES / "t9718_n1n2n3_p2022_v350_c2661-12869.json"),
    )
    assert ok.valid, ok.errors
    assert ok.stats["observations"] == 4 * 33
    assert ok.stats["dimensions"] == ["D1C", "D2C", "D3C", "D4C", "D5C"]
    wrong = connector.validate_raw(
        "ibge-sidra-9718",
        request,
        _result(SIDRA_FIXTURES / "t9718_n1n2n3_p2022_v93_c2661-12869.json"),
    )
    assert any("variáveis ['93'] diferem das esperadas ['350']" in e for e in wrong.errors)

    quilombola = connector.plan("ibge-sidra-9578", http, Watermark())
    assert [r.partition_key for r in quilombola.requests] == [
        "n1n2n3-p2022-v4709",
        "n1n2n3-p2022-v93",
        "n1n2n3-p2022-v4728",
    ]


def test_split_by_several_classifications() -> None:
    catalog = load_sources(REPO_SOURCES)
    params = SidraConnector.params(catalog.dataset("ibge-sidra-9971"))
    groups = params.request_groups()
    assert len(groups) == 3 * 19 * 3
    assert groups[0].suffix == "-c2-6794-c58-95253-c1-6795"
    assert groups[0].classifications == {
        "c1": "6795",
        "c2": "6794",
        "c58": "95253",
        "c2661": "all",
    }
    key = params.partition_key("2022", groups[-1])
    assert key == "n1n2n3n6-p2022-c2-5-c58-74120-c1-2"
    assert params.request_variables(key) == ("350",)
    assert params.estimated_values_per_period <= 50_000


def test_split_by_classification_requires_listed_categories(connector: SidraConnector) -> None:
    dataset = connector.describe("ibge-sidra-9718")
    bad = dataset.model_copy(
        update={"params": {**dataset.params, "classifications": {"c2661": "all"}}}
    )
    with pytest.raises(ConfigError, match="exige as categorias listadas"):
        connector.params(bad)


def test_classifications_in_url_and_real_fixtures(
    connector: SidraConnector, http: HttpClient
) -> None:
    race = connector.plan("ibge-sidra-9605", http, Watermark())
    assert [r.reference_period for r in race.requests] == ["2010", "2022"]
    assert race.requests[0].url.endswith("/v/93/p/2010/c86/all")
    for period in ("2010", "2022"):
        result = connector.validate_raw(
            "ibge-sidra-9605",
            _request(period),
            _result(SIDRA_FIXTURES / f"t9605_n1n2n3_p{period}.json"),
        )
        assert result.valid, result.errors
        assert result.stats["observations"] == 198
    quilombola = connector.validate_raw(
        "ibge-sidra-9578",
        ExtractionRequest("n1n2n3-p2022-v4709", "u", "a.json", reference_period="2022"),
        _result(SIDRA_FIXTURES / "t9578_n1n2n3_p2022_v4709.json"),
    )
    assert quilombola.valid, quilombola.errors
    assert quilombola.stats["variables"] == ["4709"]


def _monthly(tmp_path: Path) -> tuple[SidraConnector, HttpClient, list[str]]:
    """Série mensal sintética (formato real do SIDRA: período AAAAMM)."""
    catalog = load_sources(TEST_SOURCES)
    dataset = DatasetConfig(
        id="ibge-sidra-1737",
        source="ibge-sidra",
        official_id="1737",
        title="IPCA",
        description="teste",
        license="ibge-reuso-com-citacao",
        access_classification="public_conditional",
        periodicity="mensal",
        params={
            "table": "1737",
            "variables": ["2265"],
            "territorial_levels": ["n1"],
            "estimated_values_per_period": 12,
            "max_rows": 12,
            "refresh_recent_periods": 1,
            "period_type": "mes",
            "group_periods_by_year": True,
        },
    )
    months = [f"2025{m:02d}" for m in range(1, 13)] + ["202601", "202602"]
    header = {
        "NC": "",
        "NN": "",
        "MC": "",
        "MN": "",
        "V": "",
        "D1C": "",
        "D1N": "",
        "D2C": "",
        "D2N": "",
        "D3C": "Mês (Código)",
        "D3N": "Mês",
    }
    seen: list[str] = []

    def row(period: str) -> dict[str, str]:
        return {
            **header,
            "NC": "1",
            "NN": "Brasil",
            "MC": "2",
            "MN": "%",
            "V": "4.5",
            "D1C": "1",
            "D1N": "Brasil",
            "D2C": "2265",
            "D2N": "IPCA 12 meses",
            "D3C": period,
            "D3N": period,
        }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        asked = path.split("/p/")[1].split("/")[0]
        periods = months if asked == "all" else asked.split(",")
        return httpx.Response(200, json=[header, *(row(p) for p in periods)])

    http = HttpClient(
        HttpPolicy(min_interval_s=0, max_attempts=1), transport=httpx.MockTransport(handler)
    )
    return SidraConnector(catalog.sources["ibge-sidra"], [dataset]), http, seen


def test_monthly_periods_grouped_by_year(tmp_path: Path) -> None:
    connector, http, seen = _monthly(tmp_path)
    plan = connector.plan("ibge-sidra-1737", http, Watermark())
    assert [r.partition_key for r in plan.requests] == ["n1-p2025", "n1-p2026"]
    assert plan.requests[1].url.endswith("/p/202601,202602")
    assert [r.reference_period for r in plan.requests] == ["2025", "2026"]
    # Incremental: só o ano mais recente volta (meses novos entram na mesma partição).
    done = Watermark(partitions={r.partition_key: PartitionState() for r in plan.requests})
    again = connector.plan("ibge-sidra-1737", http, done)
    assert [r.partition_key for r in again.requests] == ["n1-p2026"]
    # Validação: meses do ano da partição, no formato AAAAMM.
    path = tmp_path / "r.json"
    path.write_bytes(http.get_bytes(plan.requests[0].url))
    ok = connector.validate_raw("ibge-sidra-1737", plan.requests[0], _result(path))
    assert ok.valid, ok.errors
    wrong = ExtractionRequest("n1-p2024", "u", "a.json", reference_period="2024")
    assert not connector.validate_raw("ibge-sidra-1737", wrong, _result(path)).valid
    assert seen


def test_period_format_and_grouping_rules() -> None:
    base = {
        "table": "1",
        "variables": ["1"],
        "territorial_levels": ["n1"],
        "estimated_values_per_period": 1,
    }
    with pytest.raises(ValueError, match="exige period_type"):
        SidraConnector.params(_ds({**base, "group_periods_by_year": True}))
    quarterly = SidraConnector.params(_ds({**base, "period_type": "trimestre"}))
    assert quarterly.period_valid("202604")
    assert not quarterly.period_valid("202605")
    monthly = SidraConnector.params(_ds({**base, "period_type": "mes"}))
    assert monthly.period_valid("202612")
    assert not monthly.period_valid("2026")


def _ds(params: dict[str, object]) -> DatasetConfig:
    return DatasetConfig(
        id="x",
        source="ibge-sidra",
        official_id="1",
        title="t",
        description="d",
        license="l",
        access_classification="public_authorized",
        periodicity="p",
        params=params,
    )


def test_detail_levels_split_total_and_categories() -> None:
    base = {
        "table": "5457",
        "variables": ["8331"],
        "territorial_levels": ["n1", "n3", "n6"],
        "estimated_values_per_period": 5633,
    }
    params = SidraConnector.params(
        _ds(
            {
                **base,
                "classifications": {"c782": "40471,2688,2689"},
                "detail_classification": "c782",
                "detail_total": "40471",
                "detail_levels": ["n1", "n3"],
            }
        )
    )
    total, detail = params.request_groups()
    assert (total.suffix, total.classifications, total.levels) == ("-t", {"c782": "40471"}, ())
    assert (detail.suffix, detail.classifications, detail.levels) == (
        "-d",
        {"c782": "2688,2689"},
        ("n1", "n3"),
    )
    assert params.request_group("n1n3n6-p2024-d").levels == ("n1", "n3")
    with pytest.raises(ValueError, match="detail_total"):
        SidraConnector.params(
            _ds(
                {
                    **base,
                    "classifications": {"c782": "2688"},
                    "detail_classification": "c782",
                    "detail_total": "40471",
                    "detail_levels": ["n1"],
                }
            )
        )


def test_extra_sets_bring_marginal_details() -> None:
    """ADR-0016: cada conjunto extra traz outra classificação, com as demais no Total."""
    base = {
        "table": "9543",
        "variables": ["2513"],
        "territorial_levels": ["n1", "n2", "n3", "n6"],
        "estimated_values_per_period": 16899,
        "classifications": {"c2": "all", "c287": "100362"},
    }
    params = SidraConnector.params(
        _ds(
            {
                **base,
                # c86 não está em classifications: a principal a deixa no Total padrão.
                "extra_sets": [{"c2": "6794", "c86": "2776,2777,2778,2779,2780"}],
                "extra_levels": ["n1", "n2", "n3"],
            }
        )
    )
    main, extra = params.request_groups()
    assert (main.suffix, main.levels) == ("", ())
    assert extra.suffix == "-xc86"  # pela classificação detalhada, não pela posição
    assert extra.classifications == {
        "c2": "6794",
        "c287": "100362",
        "c86": "2776,2777,2778,2779,2780",
    }
    assert extra.levels == ("n1", "n2", "n3")
    assert params.request_group("n1n2n3n6-p2022-xc86").levels == ("n1", "n2", "n3")
    with pytest.raises(ValueError, match="extra_levels fora"):
        SidraConnector.params(
            _ds({**base, "extra_sets": [{"c86": "2776"}], "extra_levels": ["n7"]})
        )
    with pytest.raises(ValueError, match="extra_levels exige"):
        SidraConnector.params(_ds({**base, "extra_levels": ["n1"]}))


def test_category_chunks_only_for_municipal_groups() -> None:
    """Ponto 7: categorias em lotes nos grupos com município; até UF, uma requisição."""
    params = SidraConnector.params(
        _ds(
            {
                "table": "2654",
                "variables": ["343"],
                "territorial_levels": ["n1", "n2", "n3", "n6"],
                "estimated_values_per_period": 45000,
                "classifications": {"c1836": "all"},
                "extra_sets": [
                    {"c1836": "99818", "c260": "1,2,3,4,5"},
                    {"c1836": "99818", "c2": "4,5"},
                ],
                "extra_set_levels": [[], ["n1", "n2", "n3"]],
                "category_chunk": 2,
            }
        )
    )
    suffixes = [g.suffix for g in params.request_groups()]
    assert suffixes == ["", "-xc260-k1", "-xc260-k2", "-xc260-k3", "-xc2"]
    k3 = params.request_group("n1n2n3n6-p2024-xc260-k3")
    assert k3.classifications["c260"] == "5"
