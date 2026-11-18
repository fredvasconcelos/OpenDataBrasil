from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from odb_ingestion import HttpClient, load_sources
from odb_ingestion.config import HttpPolicy
from odb_ingestion.connectors.http_file import HttpFileConnector
from odb_ingestion.contract import PartitionState, Watermark
from odb_ingestion.http import DownloadResult
from tests.ingestion_support import TEST_SOURCES, FakeSources, make_dtb_zip


@pytest.fixture
def connector() -> HttpFileConnector:
    catalog = load_sources(TEST_SOURCES)
    return HttpFileConnector(catalog.sources["ibge-geoftp"], catalog.datasets_of("ibge-geoftp"))


def _result(
    tmp_path: Path, content: bytes, content_type: str = "application/zip"
) -> DownloadResult:
    path = tmp_path / "f.zip"
    path.write_bytes(content)
    return DownloadResult(
        "u",
        200,
        {"content-type": content_type},
        datetime.now(UTC),
        path=path,
        size_bytes=len(content),
        sha256="x",
    )


def test_plan_conditional_headers(connector: HttpFileConnector) -> None:
    http = HttpClient(HttpPolicy())
    plain = connector.plan("ibge-dtb", http, Watermark())
    assert plain.requests[0].headers == {}
    assert plain.requests[0].reference_period == "2025"
    state = PartitionState(etag='"e1"', last_modified="Thu, 26 Mar 2026 21:07:36 GMT")
    cond = connector.plan("ibge-dtb", http, Watermark({"file": state}))
    assert cond.requests[0].headers == {
        "If-None-Match": '"e1"',
        "If-Modified-Since": "Thu, 26 Mar 2026 21:07:36 GMT",
    }
    assert (
        connector.plan("ibge-dtb", http, Watermark({"file": state}), full=True).requests[0].headers
        == {}
    )


def test_zip_validation(connector: HttpFileConnector, tmp_path: Path) -> None:
    req = connector.plan("ibge-dtb", HttpClient(HttpPolicy()), Watermark()).requests[0]
    ok = connector.validate_raw("ibge-dtb", req, _result(tmp_path, make_dtb_zip()))
    assert ok.valid, ok.errors
    assert "RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.xls" in ok.stats["members"]

    missing = connector.validate_raw(
        "ibge-dtb", req, _result(tmp_path, make_dtb_zip(["outro.txt"] * 1))
    )
    assert any("membro esperado ausente" in e for e in missing.errors)

    not_zip = connector.validate_raw(
        "ibge-dtb", req, _result(tmp_path, b"<html>" * 50, "text/html")
    )
    assert any("não é um ZIP" in e for e in not_zip.errors)

    tiny = connector.validate_raw("ibge-dtb", req, _result(tmp_path, b"PK"))
    assert any("mínimo esperado" in e for e in tiny.errors)

    data = bytearray(make_dtb_zip())
    data[60:80] = b"\x00" * 20  # corrompe o conteúdo do primeiro membro
    corrupted = connector.validate_raw("ibge-dtb", req, _result(tmp_path, bytes(data)))
    assert not corrupted.valid

    warn = connector.validate_raw(
        "ibge-dtb", req, _result(tmp_path, make_dtb_zip(), "application/octet-stream")
    )
    assert warn.valid
    assert warn.warnings
    assert connector.validate_raw(
        "ibge-dtb", req, DownloadResult("u", 304, {}, datetime.now(UTC))
    ).errors


def test_healthcheck(connector: HttpFileConnector) -> None:
    fake = FakeSources()
    http = HttpClient(HttpPolicy(min_interval_s=0, max_attempts=1), transport=fake.transport())
    assert connector.healthcheck(http).ok
    fake.overrides["/"] = lambda _r: httpx.Response(404)
    assert not connector.healthcheck(http).ok


def test_xlsx_and_pdf_validation(tmp_path: Path) -> None:
    """Formatos do MJSP: XLSX precisa da pasta de trabalho; PDF, da assinatura %PDF-."""
    import io  # noqa: PLC0415
    import zipfile  # noqa: PLC0415

    from odb_ingestion.config import load_sources as load  # noqa: PLC0415
    from odb_ingestion.contract import ExtractionRequest  # noqa: PLC0415

    catalog = load(Path(__file__).parents[3] / "configs" / "sources")
    conn = HttpFileConnector(
        catalog.sources["mjsp-estatistica"], catalog.datasets_of("mjsp-estatistica")
    )
    req = ExtractionRequest("file", "u", "a.xlsx", "2023", {})
    book = io.BytesIO()
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("xl/workbook.xml", "<workbook/>")
    # Estrutura válida: o único erro é o tamanho (a planilha real tem mais de 1 MB).
    small = conn.validate_raw("mjsp-sinesp-vde-2023", req, _result(tmp_path, book.getvalue()))
    assert len(small.errors) == 1
    assert "mínimo esperado 1000000" in small.errors[0]
    other = io.BytesIO()
    with zipfile.ZipFile(other, "w") as archive:
        archive.writestr("x.txt", "x")
    no_book = conn.validate_raw("mjsp-sinesp-vde-2023", req, _result(tmp_path, other.getvalue()))
    assert "XLSX sem xl/workbook.xml" in no_book.errors
    html = conn.validate_raw("mjsp-sinesp-vde-2023", req, _result(tmp_path, b"<html>erro</html>"))
    assert any("não é uma planilha XLSX" in e for e in html.errors)
    pdf_req = ExtractionRequest("file", "u", "a.pdf", "2026", {})
    pdf = conn.validate_raw(
        "mjsp-mapa-2026", pdf_req, _result(tmp_path, b"%PDF-1.7" + b"x" * 200000)
    )
    assert pdf.valid, pdf.errors
    not_pdf = conn.validate_raw(
        "mjsp-mapa-2026", pdf_req, _result(tmp_path, b"<html>" + b"x" * 200000)
    )
    assert any("%PDF-" in e for e in not_pdf.errors)
