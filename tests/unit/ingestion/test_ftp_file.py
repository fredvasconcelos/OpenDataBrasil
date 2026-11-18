"""Conector ``ftp_file`` (FTP do DATASUS), com o servidor simulado."""

from __future__ import annotations

import ftplib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from odb_ingestion import HttpError
from odb_ingestion.config import DatasetConfig, HttpPolicy, SourceConfig
from odb_ingestion.connectors import ftp_file
from odb_ingestion.connectors.ftp_file import (
    FtpFileConnector,
    FtpSession,
    RemoteFile,
    parse_dos_listing,
)
from odb_ingestion.contract import PartitionState, Watermark
from odb_ingestion.http import DownloadResult, HttpClient

# Formato real do Microsoft FTP Service do DATASUS (LIST), com nome em Latin-1.
LISTING = [
    "01-31-20  02:48PM                76107 DOAC1996.dbc",
    "12-23-25  06:48PM             29254325 DOSP2024.dbc",
    "08-24-11  12:04PM       <DIR>          CID9",
    "06-05-18  04:26PM                 1024 Tabela de Municípios-informações.pdf",
]


def _source() -> SourceConfig:
    return SourceConfig(
        id="datasus-ftp",
        name="DATASUS",
        connector="ftp_file",
        base_url="ftp://ftp.datasus.gov.br/dissemin/publicos/",
        http=HttpPolicy(min_interval_s=0, max_attempts=2, backoff_initial_s=0),
    )


def _dataset(**params: Any) -> DatasetConfig:
    return DatasetConfig(
        id="datasus-sim-cid10-dores",
        source="datasus-ftp",
        official_id="SIM/CID10/DORES",
        title="t",
        description="d",
        license="l",
        access_classification="restricted",
        periodicity="anual",
        params={
            "directory": "SIM/CID10/DORES",
            "pattern": r"DO[A-Z]{2}(?P<period>\d{4})\.dbc",
            **params,
        },
    )


def test_safe_artifact_names() -> None:
    from odb_common.storage import validate_filename  # noqa: PLC0415
    from odb_ingestion.connectors.ftp_file import artifact_name  # noqa: PLC0415

    names = ["DOSP2008.DBC", "dosp2008.dbc", "Tabela de Municípios-informações.pdf", "MORT99.HLP"]
    safe = [artifact_name(n) for n in names]
    assert safe[0].startswith("dosp2008-")
    assert safe[0].endswith(".dbc")
    assert safe[0] != safe[1]  # só a caixa difere: nomes distintos
    assert safe[2].startswith("tabela-de-municipios-informacoes-")
    assert all(validate_filename(n) for n in safe)


def test_dos_listing_parser() -> None:
    files = parse_dos_listing(LISTING)
    assert [f.name for f in files] == [
        "DOAC1996.dbc",
        "DOSP2024.dbc",
        "Tabela de Municípios-informações.pdf",
    ]
    assert files[0] == RemoteFile("DOAC1996.dbc", 76107, "2020-01-31T14:48")
    assert files[1].signature == "29254325|2025-12-23T18:48"


def test_plan_downloads_new_and_changed_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(FtpSession, "list", lambda self, d: parse_dos_listing(LISTING))
    monkeypatch.setattr(FtpSession, "close", lambda self: None)
    connector = FtpFileConnector(_source(), [_dataset()])
    with HttpClient(_source().http) as http:
        plan = connector.plan("datasus-sim-cid10-dores", http, Watermark())
        assert [r.partition_key for r in plan.requests] == ["DOAC1996.dbc", "DOSP2024.dbc"]
        first = plan.requests[0]
        assert (
            first.url == "ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/DOAC1996.dbc"
        )
        assert first.reference_period == "1996"
        assert first.headers["x-ftp-signature"] == "76107|2020-01-31T14:48"
        # Sem mudança na listagem: não baixa de novo; assinatura diferente: baixa.
        done = Watermark(
            partitions={
                "DOAC1996.dbc": PartitionState(source_version="76107|2020-01-31T14:48"),
                "DOSP2024.dbc": PartitionState(source_version="1|2020-01-01T00:00"),
            }
        )
        again = connector.plan("datasus-sim-cid10-dores", http, done)
        assert [r.partition_key for r in again.requests] == ["DOSP2024.dbc"]
        assert connector.plan("datasus-sim-cid10-dores", http, done, full=True).requests
        # Menos arquivos que o mínimo: falha a descoberta.
        strict = FtpFileConnector(_source(), [_dataset(min_files=10)])
        with pytest.raises(HttpError, match="mínimo 10"):
            strict.plan("datasus-sim-cid10-dores", http, Watermark())


def test_extract_and_validate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_download(
        self: FtpSession, directory: str, name: str, dest: Path, max_bytes: int
    ) -> tuple[int, str]:
        dest.write_bytes(b"x" * 10)
        return 10, "a" * 64

    monkeypatch.setattr(FtpSession, "download", fake_download)
    monkeypatch.setattr(FtpSession, "close", lambda self: None)
    monkeypatch.setattr(ftp_file, "dbc_summary", lambda path: {"records": 3, "fields": ["SEXO"]})
    connector = FtpFileConnector(_source(), [_dataset()])
    monkeypatch.setattr(FtpSession, "list", lambda self, d: parse_dos_listing(LISTING[:1]))
    with HttpClient(_source().http) as http:
        request = connector.plan("datasus-sim-cid10-dores", http, Watermark()).requests[0]
        result = connector.extract(request, http, tmp_path / "f.dbc")
    assert result.headers["last-modified"] == "76107|2020-01-31T14:48"
    # Tamanho diferente do listado: inválido (download truncado).
    bad = connector.validate_raw("datasus-sim-cid10-dores", request, result)
    assert not bad.valid
    assert "na listagem" in bad.errors[0]
    ok_request = type(request)(
        request.partition_key,
        request.url,
        request.artifact_name,
        request.reference_period,
        {**request.headers, "x-ftp-size": "10"},
    )
    ok = connector.validate_raw("datasus-sim-cid10-dores", ok_request, result)
    assert ok.valid, ok.errors
    assert ok.stats["records"] == 3


def test_unreadable_dbc_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "DOAC1996.dbc"
    path.write_bytes(b"isto nao e um dbc")
    connector = FtpFileConnector(_source(), [_dataset()])
    request = type("R", (), {})()
    result = DownloadResult(
        "ftp://x", 200, {}, datetime.now(UTC), path=path, size_bytes=17, sha256="b" * 64
    )
    from odb_ingestion.contract import ExtractionRequest  # noqa: PLC0415

    request = ExtractionRequest(
        "DOAC1996.dbc", "ftp://x", "DOAC1996.dbc", "1996", {"x-ftp-size": "17"}
    )
    checked = connector.validate_raw("datasus-sim-cid10-dores", request, result)
    assert not checked.valid
    assert ".dbc ilegível" in checked.errors[0]


def test_session_retries_transient_and_fails_fast_on_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    class FakeFtp:
        def retrlines(self, cmd: str, callback: Any) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError("lento")
            for line in LISTING:
                callback(line)

        def quit(self) -> None: ...

        def close(self) -> None: ...

    monkeypatch.setattr(FtpSession, "_connect", lambda self: FakeFtp())
    with HttpClient(_source().http) as http:
        session = FtpSession(_source().base_url, http)
        assert len(session.list("SIM")) == 3
        assert calls["n"] == 2

    class Refusing(FakeFtp):
        def retrlines(self, cmd: str, callback: Any) -> None:
            raise ftplib.error_perm("550 arquivo inexistente")

    monkeypatch.setattr(FtpSession, "_connect", lambda self: Refusing())
    with HttpClient(_source().http) as http:
        session = FtpSession(_source().base_url, http)
        with pytest.raises(HttpError) as refused:
            session.list("SIM")
        assert refused.value.transient is False

    class Down(FakeFtp):
        def retrlines(self, cmd: str, callback: Any) -> None:
            raise ConnectionResetError("caiu")

    monkeypatch.setattr(FtpSession, "_connect", lambda self: Down())
    with HttpClient(_source().http) as http:
        session = FtpSession(_source().base_url, http)
        with pytest.raises(HttpError) as down:
            session.list("SIM")
        assert down.value.transient is True
