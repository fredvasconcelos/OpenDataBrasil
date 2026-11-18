"""Banco de métricas de acesso (ADR-0027): estrutura, restrições e permissões.

Confere o que ``infrastructure/postgres/init/02-metrics-database.sh`` cria. As escritas
acontecem numa transação desfeita no fim, então o banco real não é alterado.
"""

import os
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError, OperationalError

from odb_catalog import make_engine
from odb_catalog.access_metrics import AccessKey, KpiCounts, MetricsReader, MetricsWriter
from odb_common.settings import Settings

pytestmark = pytest.mark.integration

_ROW = {
    "day": "2026-11-17",
    "event": "page_view",
    "country": "BR",
    "uf": 35,
    "route": "/dashboard",
    "kpi_id": "",
    "format": "",
    "referrer_domain": "",
    "count": 3,
}
_INSERT = text(
    "INSERT INTO access_daily "
    "(day, event, country, uf, route, kpi_id, format, referrer_domain, count) "
    "VALUES (:day, :event, :country, :uf, :route, :kpi_id, :format, :referrer_domain, :count) "
    "ON CONFLICT ON CONSTRAINT access_daily_pk "
    "DO UPDATE SET count = access_daily.count + EXCLUDED.count, updated_at = now()"
)


@pytest.fixture(scope="module")
def metrics_engine(pg_settings: Settings) -> Iterator[Engine]:
    engine = make_engine(pg_settings.model_copy(update={"pg_database": "odb_metrics"}))
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        engine.dispose()
        if os.environ.get("ODB_REQUIRE_INTEGRATION") == "1":
            pytest.fail(f"banco odb_metrics indisponível: {exc}")
        pytest.skip("banco odb_metrics indisponível (rode 02-metrics-database.sh)")
    yield engine
    engine.dispose()


@pytest.fixture
def conn(metrics_engine: Engine) -> Iterator[Connection]:
    with metrics_engine.connect() as c:
        tx = c.begin()
        yield c
        tx.rollback()


def _insert(conn: Connection, **changes: object) -> None:
    with conn.begin_nested():
        conn.execute(_INSERT, {**_ROW, **changes})


def test_somas_sao_acumuladas_pela_chave(conn: Connection) -> None:
    _insert(conn)
    _insert(conn, count=2)
    total = conn.execute(
        text(
            "SELECT count FROM access_daily WHERE day = :day AND uf = 35 AND route = '/dashboard'"
        ),
        {"day": _ROW["day"]},
    ).scalar_one()
    assert total == 5


@pytest.mark.parametrize(
    "changes",
    [
        {"event": "click"},  # evento fora da lista
        {"country": "br"},  # país fora do ISO 3166-1 alfa-2
        {"country": "PT", "uf": 35},  # UF só existe no Brasil
        {"uf": 99},  # código IBGE de UF inexistente
        {"event": "download", "format": ""},  # download sempre tem formato
        {"event": "page_view", "format": "csv"},  # formato só em download
        {"event": "download", "format": "pdf"},  # formato não exportado pelo portal
        {"count": -1},
    ],
)
def test_restricoes_recusam_linhas_invalidas(conn: Connection, changes: dict[str, object]) -> None:
    with pytest.raises(IntegrityError):
        _insert(conn, **changes)


def test_nao_ha_coluna_de_dado_pessoal(conn: Connection) -> None:
    cols = set(
        conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'access_daily'"
            )
        ).scalars()
    )
    assert cols == {
        "day",
        "event",
        "country",
        "uf",
        "route",
        "kpi_id",
        "format",
        "referrer_domain",
        "count",
        "updated_at",
    }


@pytest.mark.parametrize(
    ("role", "privilege", "expected"),
    [
        ("odb_metrics_writer", "SELECT", True),
        ("odb_metrics_writer", "INSERT", True),
        ("odb_metrics_writer", "UPDATE", True),
        ("odb_metrics_writer", "DELETE", False),
        ("odb_metrics_reader", "SELECT", True),
        ("odb_metrics_reader", "INSERT", False),
        ("odb_metrics_reader", "UPDATE", False),
    ],
)
def test_permissoes_da_tabela(conn: Connection, role: str, privilege: str, expected: bool) -> None:
    ok = conn.execute(
        text("SELECT has_table_privilege(:role, 'public.access_daily', :priv)"),
        {"role": role, "priv": privilege},
    ).scalar_one()
    assert ok is expected


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("odb_metrics_writer", True),
        ("odb_metrics_reader", True),
        ("odb_owner", True),
        ("odb_reader", False),  # o leitor do catálogo não enxerga as métricas
        ("odb_pipeline", False),
    ],
)
def test_quem_conecta_no_banco(conn: Connection, role: str, expected: bool) -> None:
    ok = conn.execute(
        text("SELECT has_database_privilege(:role, 'odb_metrics', 'CONNECT')"), {"role": role}
    ).scalar_one()
    assert ok is expected


# ------------------------------------------- gravação do agregador e leitura da API
# Datas de 2001: nunca colidem com contagens reais do banco local (tudo é desfeito no fim).


def _key(**changes: object) -> AccessKey:
    base: dict[str, Any] = {"day": date(2001, 11, 17), "event": "page_view", "country": "BR"}
    return AccessKey(**{**base, **changes})


def test_arquivo_e_somado_uma_vez_so(conn: Connection) -> None:
    writer = MetricsWriter(conn)
    counts = {_key(uf=35, route="/"): 3, _key(uf=0, route="/"): 2}
    assert writer.record("access-teste-1.log", "a" * 64, 5, counts) is True
    # Mesma rodada repetida (o agregador caiu antes de apagar o arquivo): nada muda.
    assert writer.record("access-teste-1.log", "a" * 64, 5, counts) is False
    assert MetricsReader(conn).views_by_uf(date(2001, 11, 17), date(2001, 11, 17)) == {35: 3, 0: 2}


def test_leituras_por_periodo_lugar_e_indicador(conn: Connection) -> None:
    day, other = date(2001, 11, 17), date(2001, 11, 10)
    MetricsWriter(conn).record(
        "access-teste-2.log",
        "b" * 64,
        9,
        {
            _key(uf=35, route="/dashboard"): 4,
            _key(country="PT", route="/"): 2,
            _key(day=other, country="AR", route="/"): 7,
            _key(event="kpi_open", uf=35, route="/dashboard", kpi_id="pib"): 6,
            _key(event="download", uf=35, route="/odb-api/exports", kpi_id="pib", format="csv"): 1,
        },
    )
    reader = MetricsReader(conn)
    assert reader.collection_started() is not None
    assert reader.totals(day, day) == {"page_view": 6, "kpi_open": 6, "download": 1}
    assert reader.views_by_country(day, day) == {"BR": 4, "PT": 2}
    assert reader.views_by_country(other, day) == {"BR": 4, "PT": 2, "AR": 7}
    assert reader.kpis(day, day) == [KpiCounts("pib", 6, 1)]


def test_tabela_de_arquivos_somados_nao_guarda_conteudo(conn: Connection) -> None:
    cols = set(
        conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'access_log_file'"
            )
        ).scalars()
    )
    assert cols == {"file_name", "sha256", "lines", "counted", "processed_at"}
    for privilege, expected in (("INSERT", True), ("DELETE", False), ("UPDATE", False)):
        ok = conn.execute(
            text("SELECT has_table_privilege('odb_metrics_writer', 'public.access_log_file', :p)"),
            {"p": privilege},
        ).scalar_one()
        assert ok is expected
    assert (
        conn.execute(
            text(
                "SELECT has_table_privilege("
                "'odb_metrics_reader', 'public.access_log_file', 'SELECT')"
            )
        ).scalar_one()
        is False
    )
