"""Classificação do log de acesso do Caddy e ciclo do agregador (ADR-0027)."""

import gzip
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from odb_catalog.access_metrics import AccessKey
from odb_cli.access_log import aggregate, classify, day_of, is_robot, location
from odb_cli.metrics import MAX_AGE_S, rolled_files, run_cycle

HOST = "beta.opendatabrasil.org"
SITE = f"https://{HOST}"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
# 2026-11-17 15:00 em Brasília (18:00 UTC).
TS = datetime(2026, 11, 17, 18, 0, tzinfo=UTC).timestamp()
DAY = date(2026, 11, 17)


def line(
    uri: str,
    *,
    method: str = "GET",
    status: int = 200,
    ts: float = TS,
    **fields: str,
) -> dict[str, Any]:
    """Uma linha como o Caddyfile da Vitrine grava (sem IP nem cabeçalhos)."""
    base = {"country": "BR", "region": "SP", "referer": "", "ua": UA, "rsc": "", "prefetch": ""}
    return {
        "ts": ts,
        "request": {"method": method, "uri": uri, "host": HOST, "proto": "HTTP/2.0"},
        "status": status,
        **base,
        **fields,
    }


def events(entry: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [(k.event, k.route, k.kpi_id) for k in classify(entry)]


# ------------------------------------------------------------------ visualizações


def test_document_load_counts_one_view_with_external_origin() -> None:
    keys = classify(line("/sobre", referer="https://www.google.com/"))
    assert keys == [
        AccessKey(DAY, "page_view", "BR", 35, route="/sobre", referrer_domain="www.google.com")
    ]


def test_internal_navigation_keeps_origin_empty() -> None:
    keys = classify(line("/sobre", referer=f"{SITE}/", rsc="1"))
    assert [(k.event, k.referrer_domain) for k in keys] == [("page_view", "")]


def test_filter_change_on_same_route_is_not_a_new_view() -> None:
    # Trocar nível ou período no painel faz router.replace na mesma rota (RSC).
    entry = line(
        "/dashboard?kpi=pib&nivel=uf&_rsc=abc",
        rsc="1",
        referer=f"{SITE}/dashboard?kpi=pib&nivel=brasil",
    )
    assert events(entry) == []


@pytest.mark.parametrize(
    "fields",
    [
        {"prefetch": "1", "rsc": "1"},  # prefetch do Next.js
        {"purpose": "prefetch"},  # prefetch do navegador
        {"ua": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"},
        {"ua": "WhatsApp/2.23"},
        {"ua": "curl/8.10"},
        {"ua": ""},
    ],
)
def test_prefetch_and_robots_do_not_count(fields: dict[str, str]) -> None:
    entry = line("/sobre")
    entry.update(fields)
    assert events(entry) == []


@pytest.mark.parametrize(
    ("uri", "status", "method"),
    [
        ("/_next/static/chunks/app.js", 200, "GET"),
        ("/odb-api/kpis/pib/map", 200, "GET"),
        ("/bandeiras-uf/sp.svg", 200, "GET"),
        ("/robots.txt", 200, "GET"),
        ("/_odb/tick", 204, "GET"),
        ("/wp-admin", 404, "GET"),
        ("/sobre", 200, "HEAD"),
        ("/sobre", 304, "GET"),
    ],
)
def test_non_pages_do_not_count(uri: str, status: int, method: str) -> None:
    assert events(line(uri, status=status, method=method)) == []


def test_route_drops_query_and_trailing_slash() -> None:
    assert events(line("/apoie/?utm_source=x")) == [("page_view", "/apoie", "")]


# ------------------------------------------------------------- aberturas de KPI


def test_dashboard_document_with_kpi_counts_view_and_open() -> None:
    assert events(line("/dashboard?kpi=populacao_estimada")) == [
        ("page_view", "/dashboard", ""),
        ("kpi_open", "/dashboard", "populacao_estimada"),
    ]


def test_switching_kpi_in_the_dashboard_counts_an_open_only() -> None:
    entry = line(
        "/dashboard?kpi=pib&_rsc=1",
        rsc="1",
        referer=f"{SITE}/dashboard?kpi=populacao_estimada",
    )
    assert events(entry) == [("kpi_open", "/dashboard", "pib")]


def test_coming_from_another_page_counts_view_and_open() -> None:
    entry = line("/dashboard?kpi=pib", rsc="1", referer=f"{SITE}/")
    assert events(entry) == [("page_view", "/dashboard", ""), ("kpi_open", "/dashboard", "pib")]


def test_invalid_kpi_id_is_ignored() -> None:
    assert events(line("/dashboard?kpi=../../etc")) == [("page_view", "/dashboard", "")]


# ------------------------------------------------------------------ downloads


def test_export_counts_download_with_kpi_and_format() -> None:
    entry = line(
        "/odb-api/exports",
        method="POST",
        export_kpi="pib",
        export_format="xlsx",
    )
    assert classify(entry) == [
        AccessKey(DAY, "download", "BR", 35, route="/odb-api/exports", kpi_id="pib", format="xlsx")
    ]


@pytest.mark.parametrize(("status", "fmt"), [(413, "csv"), (200, ""), (200, "exe")])
def test_failed_or_unknown_export_does_not_count(status: int, fmt: str) -> None:
    entry = line(
        "/odb-api/exports", method="POST", status=status, export_kpi="pib", export_format=fmt
    )
    assert classify(entry) == []


# --------------------------------------------------------------- local e dia


@pytest.mark.parametrize(
    ("country", "region", "expected"),
    [
        ("BR", "SP", ("BR", 35)),
        ("br", "BR-RJ", ("BR", 33)),
        ("BR", "DF", ("BR", 53)),
        ("BR", "", ("BR", 0)),  # sem a transformação da Cloudflare: UF desconhecida
        ("BR", "ZZ", ("BR", 0)),
        ("PT", "11", ("PT", 0)),  # UF só no Brasil
        ("XX", "", ("ZZ", 0)),
        ("T1", "", ("ZZ", 0)),  # Tor
        ("", "", ("ZZ", 0)),
    ],
)
def test_location(country: str, region: str, expected: tuple[str, int]) -> None:
    assert location(country, region) == expected


def test_day_is_in_brasilia_time() -> None:
    # 02:00 UTC do dia 18 ainda é dia 17 em Brasília.
    assert day_of(datetime(2026, 11, 18, 2, 0, tzinfo=UTC).timestamp()) == date(2026, 11, 17)


def test_is_robot() -> None:
    assert not is_robot(UA)
    assert is_robot("Mozilla/5.0 (X11) AppleWebKit/537.36 HeadlessChrome/140.0")


def test_aggregate_sums_and_counts_invalid_lines() -> None:
    lines = [
        json.dumps(line("/sobre")),
        json.dumps(line("/sobre")),
        "não é json",
        "[1, 2]",
        "",
    ]
    counts, total, invalid = aggregate(lines)
    assert total == 4
    assert invalid == 2
    assert counts == {AccessKey(DAY, "page_view", "BR", 35, route="/sobre"): 2}


# ------------------------------------------------------------- ciclo do agregador


class FakeRecorder:
    def __init__(self, fail: bool = False) -> None:
        self.files: dict[str, dict[AccessKey, int]] = {}
        self.fail = fail

    def record(self, file_name: str, sha256: str, lines: int, counts: dict[AccessKey, int]) -> bool:
        if self.fail:
            raise ConnectionError("banco fora do ar")
        assert len(sha256) == 64
        if file_name in self.files:
            return False
        self.files[file_name] = counts
        return True


def write_log(path: Path, n: int, *, gz: bool = False) -> Path:
    body = "".join(json.dumps(line("/sobre")) + "\n" for _ in range(n)).encode()
    path.write_bytes(gzip.compress(body) if gz else body)
    return path


def test_cycle_counts_rolled_files_deletes_them_and_keeps_the_active(tmp_path: Path) -> None:
    write_log(tmp_path / "access.log", 5)
    write_log(tmp_path / "access-2026-11-17T10-00-00.000.log", 2)
    write_log(tmp_path / "access-2026-11-17T11-00-00.000.log.gz", 3, gz=True)
    recorder = FakeRecorder()
    report = run_cycle(tmp_path, recorder)
    assert (report.files, report.lines, report.counted, report.error) == (2, 5, 5, None)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["access.log"]
    assert sum(sum(c.values()) for c in recorder.files.values()) == 5


def test_file_already_counted_is_only_deleted(tmp_path: Path) -> None:
    # O agregador caiu entre a gravação e a remoção: a próxima rodada não conta de novo.
    name = "access-2026-11-17T10-00-00.000.log"
    recorder = FakeRecorder()
    recorder.files[name] = {}
    write_log(tmp_path / name, 4)
    report = run_cycle(tmp_path, recorder)
    assert (report.already, report.counted) == (1, 0)
    assert not (tmp_path / name).exists()


def test_database_down_keeps_recent_files_and_drops_old_ones(tmp_path: Path) -> None:
    recent = write_log(tmp_path / "access-2026-11-17T10-00-00.000.log", 1)
    old = write_log(tmp_path / "access-2026-11-16T09-00-00.000.log", 1)
    now = recent.stat().st_mtime
    os.utime(old, (now - MAX_AGE_S - 60, now - MAX_AGE_S - 60))
    report = run_cycle(tmp_path, FakeRecorder(fail=True), now=now)
    assert report.error is not None
    assert report.discarded == [old.name]
    assert recent.exists()
    assert not old.exists()


def test_rolled_files_ignores_other_names(tmp_path: Path) -> None:
    for name in ("access.log", "outro.log", "access-1.log", "access-2.log.gz", "access-3.txt"):
        (tmp_path / name).write_text("")
    assert [p.name for p in rolled_files(tmp_path)] == ["access-1.log", "access-2.log.gz"]
