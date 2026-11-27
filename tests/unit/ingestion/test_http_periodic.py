"""Conector ``http_periodic``: um arquivo por período, com revisão retroativa (ADR-0030)."""

import io
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from odb_common.storage import LakehouseLayout
from odb_ingestion import BronzeStore, HttpClient, IngestionRunner, build_connectors
from odb_ingestion.config import ConfigError, HttpPolicy, SourceCatalog, SourcesFile
from odb_ingestion.connectors.http_periodic import (
    HttpPeriodicConnector,
    current_period,
    periods_between,
    reference_period,
)
from odb_ingestion.contract import BaseConnector, PartitionState, Watermark
from odb_ingestion.http import DownloadResult, HttpError
from tests.ingestion_support import InMemoryRegistry

HOST = "arquivos.exemplo.gov.br"
COLUMNS = ("Código Favorecido", "Nome Favorecido", "Valor Recebido")
HEADER = ";".join(f'"{c}"' for c in COLUMNS)


def _csv(header: str = HEADER, rows: int = 2, marker: str = "") -> bytes:
    lines = [header] + [f'"{i:014d}";"ÓRGÃO {i}{marker}";"{i},50"' for i in range(rows)]
    return ("\r\n".join(lines) + "\r\n").encode("latin-1")


def _zip(period: str, csv_bytes: bytes | None = None, *, comment: bytes = b"") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{period}_Recebimentos.csv", csv_bytes or _csv())
        archive.comment = comment
    return buf.getvalue()


def _catalog(**overrides: Any) -> SourceCatalog:
    params: dict[str, Any] = {
        "url_template": f"https://{HOST}/saida/fav/{{period}}_Despesas.zip",
        "artifact_template": "favorecidos-{period}.zip",
        "grain": "month",
        "start": "202411",
        "end": "202501",
        "format": "zip",
        "expected_members": ["{period}_Recebimentos.csv"],
        "csv": [
            {
                "member": "{period}_Recebimentos.csv",
                "encoding": "latin-1",
                "delimiter": ";",
                "columns": list(COLUMNS),
            }
        ],
        "min_bytes": 50,
        "healthcheck_url": f"https://{HOST}/saida/fav/202411_Despesas.zip",
    }
    params.update(overrides)
    data = {
        "config_version": "1.0.0",
        "institution": {"id": "teste", "name": "Teste", "acronym": "T", "url": "https://t"},
        "licenses": [
            {"id": "lic", "name": "Lic", "conditions": "crédito", "review_status": "approved"}
        ],
        "sources": [
            {
                "id": "arquivos",
                "name": "Arquivos",
                "connector": "http_periodic",
                "base_url": f"https://{HOST}/saida/",
                "http": {
                    "min_interval_s": 0.0,
                    "max_attempts": 2,
                    "backoff_initial_s": 0.0,
                    "halt_on_status": [405],
                },
            }
        ],
        "datasets": [
            {
                "id": "fav",
                "source": "arquivos",
                "official_id": "despesas-favorecidos",
                "title": "Favorecidos",
                "description": "teste",
                "license": "lic",
                "access_classification": "public_conditional",
                "periodicity": "mensal",
                "params": params,
            },
            {
                "id": "fav2",
                "source": "arquivos",
                "official_id": "outra-base",
                "title": "Outra base da mesma fonte",
                "description": "teste",
                "license": "lic",
                "access_classification": "public_conditional",
                "periodicity": "mensal",
                "params": {
                    **params,
                    "url_template": f"https://{HOST}/saida/outra/{{period}}_Despesas.zip",
                    "artifact_template": "outra-{period}.zip",
                },
            },
        ],
    }
    return SourceCatalog([SourcesFile.model_validate(data)])


@dataclass
class FakeFiles:
    """Servidor de arquivos com ETag por arquivo, como um bucket S3."""

    files: dict[str, tuple[bytes, str]] = field(default_factory=dict)
    requests: list[httpx.Request] = field(default_factory=list)

    def put(self, period: str, content: bytes, etag: str) -> None:
        self.files[f"/saida/fav/{period}_Despesas.zip"] = (content, etag)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        found = self.files.get(request.url.path)
        if found is None:
            return httpx.Response(403, content=b"<Error>AccessDenied</Error>")
        content, etag = found
        if request.headers.get("if-none-match") == etag:
            return httpx.Response(304, headers={"etag": etag})
        if request.headers.get("range") == "bytes=0-0":
            return httpx.Response(206, content=content[:1], headers={"etag": etag})
        return httpx.Response(
            200,
            content=content,
            headers={
                "content-type": "application/zip",
                "etag": etag,
                "last-modified": "Sat, 07 Nov 2026 22:24:51 GMT",
            },
        )


def _connector(catalog: SourceCatalog) -> HttpPeriodicConnector:
    return HttpPeriodicConnector(catalog.sources["arquivos"], catalog.datasets_of("arquivos"))


def _result(tmp_path: Path, content: bytes, name: str = "a.zip") -> DownloadResult:
    path = tmp_path / name
    path.write_bytes(content)
    return DownloadResult(
        "u",
        200,
        {"content-type": "application/zip"},
        datetime.now(UTC),
        path=path,
        size_bytes=len(content),
        sha256="x",
    )


def test_periods_between_crosses_year_and_validates_format() -> None:
    assert periods_between("month", "202411", "202502") == ["202411", "202412", "202501", "202502"]
    assert periods_between("year", "2024", "2025") == ["2024", "2025"]
    assert periods_between("month", "202503", "202502") == []
    with pytest.raises(ValueError, match="AAAAMM"):
        periods_between("month", "2024-01", "202402")
    with pytest.raises(ValueError, match="AAAAMM"):
        periods_between("month", "202413", "202501")
    assert reference_period("month", "202401") == "2024-01"
    assert reference_period("year", "2024") == "2024"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"url_template": "https://h/fixo.zip"}, "url_template precisa conter"),
        ({"start": "202502", "end": "202501"}, "intervalo vazio"),
        ({"format": "binary"}, "contrato csv exige"),
        ({"csv": [{"columns": ["a"]}]}, "cada contrato csv indica o membro"),
        ({"artifact_template": "{period}_Despesas.zip"}, "nome de arquivo inválido"),
    ],
)
def test_invalid_params_fail_at_load(override: dict[str, Any], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        _connector(_catalog(**override))


def test_plan_one_conditional_request_per_known_period() -> None:
    connector = _connector(_catalog())
    http = HttpClient(HttpPolicy())
    plan = connector.plan("fav", http, Watermark())
    assert [r.partition_key for r in plan.requests] == ["202411", "202412", "202501"]
    assert plan.requests[0].url == f"https://{HOST}/saida/fav/202411_Despesas.zip"
    assert plan.requests[2].artifact_name == "favorecidos-202501.zip"
    assert plan.requests[2].reference_period == "2025-01"
    assert all(r.headers == {} for r in plan.requests)

    state = PartitionState(etag='"e1"', last_modified="Sat, 07 Nov 2026 22:24:51 GMT")
    plan = connector.plan("fav", http, Watermark({"202412": state}))
    assert plan.requests[0].headers == {}
    assert plan.requests[1].headers == {
        "If-None-Match": '"e1"',
        "If-Modified-Since": "Sat, 07 Nov 2026 22:24:51 GMT",
    }
    assert plan.notes == ("1 requisições condicionais",)
    full = connector.plan("fav", http, Watermark({"202412": state}), full=True)
    assert all(r.headers == {} for r in full.requests)


def test_zip_validation_checks_members_header_and_records_member_sha(tmp_path: Path) -> None:
    connector = _connector(_catalog())
    request = connector.plan("fav", HttpClient(HttpPolicy()), Watermark()).requests[0]
    ok = connector.validate_raw("fav", request, _result(tmp_path, _zip("202411")))
    assert ok.valid, ok.errors
    assert ok.stats["members"] == ["202411_Recebimentos.csv"]
    member_sha = ok.stats["member_sha256"]
    assert isinstance(member_sha, dict)
    assert len(member_sha["202411_Recebimentos.csv"]) == 64

    wrong_period = connector.validate_raw("fav", request, _result(tmp_path, _zip("202412"), "b"))
    assert any("membro esperado ausente: 202411_Recebimentos.csv" in e for e in wrong_period.errors)

    renamed = HEADER.replace("Valor Recebido", "Valor Pago")
    drift = connector.validate_raw(
        "fav", request, _result(tmp_path, _zip("202411", _csv(renamed)), "c")
    )
    assert any("novas: ['Valor Pago']" in e and "ausentes: ['Valor Recebido']" in e
               for e in drift.errors)  # fmt: skip

    reordered = ";".join(f'"{c}"' for c in reversed(COLUMNS))
    order = connector.validate_raw(
        "fav", request, _result(tmp_path, _zip("202411", _csv(reordered)), "d")
    )
    assert any("outra ordem" in e for e in order.errors)

    html = connector.validate_raw("fav", request, _result(tmp_path, b"<html>403</html>" * 9, "e"))
    assert any("não é um ZIP" in e for e in html.errors)

    tiny = connector.validate_raw("fav", request, _result(tmp_path, b"PK", "f"))
    assert any("mínimo esperado" in e for e in tiny.errors)


def test_zip_with_bad_crc_is_rejected(tmp_path: Path) -> None:
    connector = _connector(_catalog())
    request = connector.plan("fav", HttpClient(HttpPolicy()), Watermark()).requests[0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("202411_Recebimentos.csv", _csv(rows=30))
    data = bytearray(buf.getvalue())
    start = data.index(b"ORGAO".replace(b"ORGAO", "ÓRGÃO 5".encode("latin-1")))
    data[start : start + 3] = b"XXX"  # mesmo tamanho, CRC diferente
    result = connector.validate_raw("fav", request, _result(tmp_path, bytes(data)))
    assert any("corrompido" in e for e in result.errors)


def test_csv_format_checks_header_in_declared_encoding(tmp_path: Path) -> None:
    catalog = _catalog(
        format="csv",
        expected_members=[],
        url_template=f"https://{HOST}/saida/acao{{period}}.csv",
        artifact_template="acao{period}.csv",
        grain="year",
        start="2024",
        end="2025",
        csv=[{"encoding": "latin-1", "delimiter": ";", "columns": list(COLUMNS)}],
    )
    connector = _connector(catalog)
    request = connector.plan("fav", HttpClient(HttpPolicy()), Watermark()).requests[0]
    assert request.partition_key == "2024"
    plain = ";".join(COLUMNS)  # sem aspas, como o SIOP
    ok = connector.validate_raw("fav", request, _result(tmp_path, _csv(plain), "a.csv"))
    assert ok.valid, ok.errors
    utf8_bom = b"\xef\xbb\xbf" + plain.encode("utf-8")
    wrong = connector.validate_raw("fav", request, _result(tmp_path, utf8_bom * 4, "b.csv"))
    assert not wrong.valid  # em latin-1, o BOM vira texto e o cabeçalho diverge


class Env:
    def __init__(self, tmp_path: Path) -> None:
        self.catalog = _catalog()
        self.files = FakeFiles()
        self.registry = InMemoryRegistry()
        self.bronze = BronzeStore(LakehouseLayout((tmp_path / "lake").as_uri()))

        def factory(connector: BaseConnector) -> HttpClient:
            return HttpClient(
                connector.source.http,
                transport=httpx.MockTransport(self.files.handler),
                sleep=lambda _s: None,
            )

        self.runner = IngestionRunner(
            self.catalog, build_connectors(self.catalog), self.bronze, self.registry, factory
        )

    def bronze_files(self) -> list[Path]:
        return sorted(p for p in self.bronze.bronze_root.rglob("*") if p.is_file())


def test_cycle_detects_retroactive_revision_of_one_month(tmp_path: Path) -> None:
    env = Env(tmp_path)
    for period in ("202411", "202412", "202501"):
        env.files.put(period, _zip(period), f'"{period}-v1"')

    first = env.runner.run("fav")
    assert first.status == "succeeded", first.error
    assert first.counts == {"stored": 3}
    assert len(env.bronze_files()) == 3

    # Ciclo seguinte sem mudança: tudo 304, nada baixado nem gravado.
    second = env.runner.run("fav")
    assert second.status == "succeeded", second.error
    assert second.counts == {"not_modified": 3}
    assert second.bytes_stored == 0
    assert len(env.bronze_files()) == 3

    # A fonte revisa dezembro (conteúdo novo): só ele volta, os outros seguem 304.
    env.files.put("202412", _zip("202412", _csv(marker=" REVISADO")), '"202412-v2"')
    third = env.runner.run("fav")
    assert third.status == "succeeded", third.error
    assert third.counts == {"not_modified": 2, "stored": 1}
    assert len(env.bronze_files()) == 4  # a versão anterior continua preservada
    revised = env.registry.by_status("stored")[-1]
    assert revised.partition_key == "202412"
    assert revised.reference_period == "2024-12"
    assert env.registry.get_watermark("fav").partitions["202412"].etag == '"202412-v2"'


def test_regenerated_zip_with_same_csv_keeps_member_checksum(tmp_path: Path) -> None:
    """ZIP com bytes novos e CSV igual: novo artefato, mesmo SHA-256 do membro."""
    env = Env(tmp_path)
    env.files.put("202411", _zip("202411"), '"v1"')
    env.files.put("202412", _zip("202412"), '"v1"')
    env.files.put("202501", _zip("202501"), '"v1"')
    assert env.runner.run("fav").status == "succeeded"
    env.files.put("202411", _zip("202411", comment=b"regerado"), '"v2"')
    report = env.runner.run("fav")
    assert report.counts == {"not_modified": 2, "stored": 1}
    a, b = (r for r in env.registry.by_status("stored") if r.partition_key == "202411")
    assert a.checksum_sha256 != b.checksum_sha256
    assert a.validation["stats"]["member_sha256"] == b.validation["stats"]["member_sha256"]


def test_missing_period_fails_without_moving_watermark(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.files.put("202411", _zip("202411"), '"v1"')
    env.files.put("202412", _zip("202412"), '"v1"')  # 202501 ainda não publicado (403)
    report = env.runner.run("fav")
    assert report.status == "failed"
    assert report.counts == {"stored": 2, "failed": 1}
    assert env.registry.get_watermark("fav").partitions == {}


def test_healthcheck_reads_one_byte_of_known_file(tmp_path: Path) -> None:
    env = Env(tmp_path)
    env.files.put("202411", _zip("202411"), '"v1"')
    connector = _connector(env.catalog)
    with HttpClient(
        HttpPolicy(min_interval_s=0.0), transport=httpx.MockTransport(env.files.handler)
    ) as http:
        status = connector.healthcheck(http)
    assert status.ok, status.detail
    assert env.files.requests[-1].headers["range"] == "bytes=0-0"


def test_block_status_halts_the_source_without_more_requests(tmp_path: Path) -> None:
    """Caso real da CGU (2026-11-22): 405 "Human Verification" no meio da série."""
    env = Env(tmp_path)
    env.files.put("202411", _zip("202411"), '"v1"')
    blocked = "/saida/fav/202412_Despesas.zip"
    page = b"<title>Human Verification</title>"

    seen_block: list[bool] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == blocked or seen_block:  # depois do bloqueio, tudo é 405
            seen_block.append(True)
            env.files.requests.append(request)
            return httpx.Response(405, content=page)
        return env.files.handler(request)

    env.files.put("202501", _zip("202501"), '"v1"')
    env.runner = IngestionRunner(
        env.catalog,
        build_connectors(env.catalog),
        env.bronze,
        env.registry,
        lambda c: HttpClient(
            c.source.http, transport=httpx.MockTransport(handler), sleep=lambda _s: None
        ),
    )
    first, second = env.runner.run_many(["fav", "fav2"])
    assert first.status == second.status == "failed"
    assert first.halted
    assert second.halted
    assert first.counts == {"stored": 1, "failed": 1}  # 202501 nem foi pedido
    assert "HTTP 405 em 202412" in (first.error or "")
    assert second.counts == {}
    assert "fonte arquivos bloqueou" in (second.error or "")
    assert [r.url.path for r in env.files.requests] == [
        "/saida/fav/202411_Despesas.zip",
        blocked,
    ]
    assert env.registry.get_watermark("fav").partitions == {}


def test_challenge_with_202_is_an_http_error_not_an_artifact(tmp_path: Path) -> None:
    connector = _connector(_catalog())
    request = connector.plan("fav", HttpClient(HttpPolicy()), Watermark()).requests[0]
    transport = httpx.MockTransport(lambda _r: httpx.Response(202, content=b""))
    with (
        HttpClient(HttpPolicy(min_interval_s=0.0), transport=transport) as http,
        pytest.raises(HttpError, match="HTTP 202 inesperado") as info,
    ):
        connector.extract(request, http, tmp_path / "x.zip")
    assert info.value.status == 202
    assert not (tmp_path / "x.zip").exists()


def test_current_period_uses_brasilia_time() -> None:
    # 01:00 UTC de 1º de dezembro ainda é 30 de novembro em Brasília.
    assert current_period("month", datetime(2026, 12, 1, 1, 0, tzinfo=UTC)) == "202611"
    assert current_period("month", datetime(2026, 12, 1, 4, 0, tzinfo=UTC)) == "202612"
    assert current_period("year", datetime(2027, 1, 1, 2, 0, tzinfo=UTC)) == "2026"


def _current_env(tmp_path: Path, today: datetime) -> Env:
    env = Env(tmp_path)
    env.catalog = _catalog(start="202410", end="atual")
    connectors = build_connectors(env.catalog)
    clocked = HttpPeriodicConnector(
        env.catalog.sources["arquivos"], env.catalog.datasets_of("arquivos"), clock=lambda: today
    )
    connectors["arquivos"] = clocked
    env.runner = IngestionRunner(
        env.catalog,
        connectors,
        env.bronze,
        env.registry,
        lambda c: HttpClient(
            c.source.http, transport=httpx.MockTransport(env.files.handler), sleep=lambda _s: None
        ),
    )
    return env


def test_current_period_not_yet_published_is_left_for_next_run(tmp_path: Path) -> None:
    env = _current_env(tmp_path, datetime(2024, 12, 1, 12, 0, tzinfo=UTC))
    env.files.put("202410", _zip("202410"), '"v1"')
    env.files.put("202411", _zip("202411"), '"v1"')  # 202412 ainda não existe: 403 do bucket
    report = env.runner.run("fav")
    assert report.status == "succeeded", report.error
    assert report.planned == 2
    assert report.counts == {"stored": 2}
    assert any("202412 ainda não publicado" in n for n in report.notes)

    # No dia seguinte, a fonte publica dezembro: entra; os outros respondem 304.
    env.files.put("202412", _zip("202412"), '"v1"')
    report = env.runner.run("fav")
    assert report.counts == {"not_modified": 2, "stored": 1}
    sent = len(env.files.requests)

    # Com o período corrente já conhecido, não há sondagem: só os pedidos condicionais.
    report = env.runner.run("fav")
    assert report.counts == {"not_modified": 3}
    assert len(env.files.requests) - sent == 3
    assert not any(r.headers.get("range") for r in env.files.requests[sent:])


def test_block_during_probe_halts_the_source(tmp_path: Path) -> None:
    env = _current_env(tmp_path, datetime(2024, 12, 1, 12, 0, tzinfo=UTC))

    def blocked(request: httpx.Request) -> httpx.Response:
        env.files.requests.append(request)
        return httpx.Response(405, content=b"<title>Human Verification</title>")

    env.files.handler = blocked  # type: ignore[method-assign]
    first, second = env.runner.run_many(["fav", "fav2"])
    assert first.halted
    assert second.halted
    assert "no plano" in (first.error or "")
    assert len(env.files.requests) == 1  # só a sondagem do primeiro dataset
