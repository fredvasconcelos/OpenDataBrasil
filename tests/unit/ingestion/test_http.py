import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from odb_ingestion.config import HttpPolicy
from odb_ingestion.http import HttpClient, HttpError, _retry_after_seconds


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def _client(
    handler: Callable[[httpx.Request], httpx.Response], clock: Clock, **policy: object
) -> HttpClient:
    base: dict[str, object] = {"min_interval_s": 0.0, "backoff_initial_s": 1.0, "max_attempts": 3}
    base.update(policy)
    return HttpClient(
        HttpPolicy(**base),  # type: ignore[arg-type]
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep,
        clock=clock,
    )


def _sequence(*responses: httpx.Response | Exception) -> Callable[[httpx.Request], httpx.Response]:
    items = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        item = items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return handler


def test_download_streams_with_checksum_and_headers(tmp_path: Path) -> None:
    body = b"conteudo" * 1000
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=body, headers={"etag": '"e1"', "x-other": "drop"})

    with _client(handler, Clock(), user_agent="UA-teste") as http:
        result = http.download("https://h/a", tmp_path / "a.bin", headers={"If-None-Match": '"e0"'})
    assert result.sha256 == hashlib.sha256(body).hexdigest()
    assert result.size_bytes == len(body)
    assert (tmp_path / "a.bin").read_bytes() == body
    assert result.headers == {"etag": '"e1"', "content-length": str(len(body))}
    assert seen[0].headers["user-agent"] == "UA-teste"
    assert seen[0].headers["if-none-match"] == '"e0"'
    assert not result.not_modified


def test_not_modified_creates_no_file(tmp_path: Path) -> None:
    with _client(_sequence(httpx.Response(304)), Clock()) as http:
        result = http.download("https://h/a", tmp_path / "a.bin")
    assert result.not_modified
    assert result.path is None
    assert not (tmp_path / "a.bin").exists()


def test_retries_5xx_with_backoff(tmp_path: Path) -> None:
    clock = Clock()
    handler = _sequence(
        httpx.Response(503), httpx.Response(502), httpx.Response(200, content=b"ok")
    )
    with _client(handler, clock) as http:
        result = http.download("https://h/a", tmp_path / "a")
    assert result.attempts == 3
    assert len(clock.sleeps) == 2
    assert 1.0 <= clock.sleeps[0] <= 1.25
    assert 2.0 <= clock.sleeps[1] <= 2.5


def test_429_respects_retry_after(tmp_path: Path) -> None:
    clock = Clock()
    handler = _sequence(
        httpx.Response(429, headers={"retry-after": "7"}), httpx.Response(200, content=b"ok")
    )
    with _client(handler, clock) as http:
        http.download("https://h/a", tmp_path / "a")
    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] >= 7


def test_retry_after_above_limit_aborts(tmp_path: Path) -> None:
    handler = _sequence(httpx.Response(429, headers={"retry-after": "9999"}))
    with (
        _client(handler, Clock(), max_retry_after_s=60) as http,
        pytest.raises(HttpError, match="Retry-After") as info,
    ):
        http.download("https://h/a", tmp_path / "a")
    assert info.value.status == 429


def test_client_errors_are_not_retried(tmp_path: Path) -> None:
    clock = Clock()
    handler = _sequence(httpx.Response(400, content=b"Tabela invalida"))
    with (
        _client(handler, clock) as http,
        pytest.raises(HttpError, match="Tabela invalida") as info,
    ):
        http.download("https://h/a", tmp_path / "a")
    assert info.value.status == 400
    assert clock.sleeps == []


def test_transport_errors_exhaust_attempts(tmp_path: Path) -> None:
    clock = Clock()
    handler = _sequence(*[httpx.ConnectTimeout("t")] * 3)
    with _client(handler, clock) as http, pytest.raises(HttpError, match="3 tentativas"):
        http.download("https://h/a", tmp_path / "a")
    assert len(clock.sleeps) == 2
    handler = _sequence(*[httpx.Response(500)] * 3)
    with _client(handler, Clock()) as http, pytest.raises(HttpError, match="HTTP 500") as info:
        http.download("https://h/a", tmp_path / "b")
    assert info.value.status == 500


def test_size_limit_removes_partial_file(tmp_path: Path) -> None:
    handler = _sequence(httpx.Response(200, content=b"x" * 100))
    with _client(handler, Clock()) as http, pytest.raises(HttpError, match="excede"):
        http.download("https://h/a", tmp_path / "a", max_bytes=10)
    assert not (tmp_path / "a").exists()
    handler = _sequence(httpx.Response(200, content=b"x" * 100))
    with _client(handler, Clock()) as http, pytest.raises(HttpError, match="excede"):
        http.get_bytes("https://h/a", max_bytes=10)


def test_existing_destination_is_never_overwritten(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"original")
    handler = _sequence(httpx.Response(200, content=b"novo"))
    with _client(handler, Clock()) as http, pytest.raises(FileExistsError):
        http.download("https://h/a", tmp_path / "a")
    assert (tmp_path / "a").read_bytes() == b"original"


def test_min_interval_per_host(tmp_path: Path) -> None:
    clock = Clock()
    handler = _sequence(*[httpx.Response(200, content=b"ok")] * 3)
    with _client(handler, clock, min_interval_s=2.0) as http:
        assert http.get_bytes("https://h1/a") == b"ok"
        http.get_bytes("https://h1/b")
        http.get_bytes("https://h2/c")  # outro host: sem espera
    assert clock.sleeps == [2.0]


def test_retry_after_parsing() -> None:
    now = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
    assert _retry_after_seconds("5", now) == 5
    assert _retry_after_seconds("Tue, 03 Nov 2026 12:00:30 GMT", now) == 30
    assert _retry_after_seconds("Tue, 03 Nov 2026 11:00:00 GMT", now) == 0
    assert _retry_after_seconds("lixo", now) is None
    assert _retry_after_seconds(None, now) is None
