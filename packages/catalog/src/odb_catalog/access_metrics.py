"""Banco de métricas de acesso ``odb_metrics`` (ADR-0027): gravação e leitura das somas.

O banco é da Vitrine e fica fora do catálogo (o ``deploy.sh`` restaura o catálogo com
``--clean`` e nunca toca outro banco). Nenhuma coluna guarda dado pessoal: só somas por
dia, evento, país, UF, rota, indicador, formato e domínio de origem.

- ``MetricsWriter``: só o agregador do log (papel ``odb_metrics_writer``).
- ``MetricsReader``: só a API (papel ``odb_metrics_reader``).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import Connection, Engine, create_engine, text

from odb_common.settings import Settings

Event = Literal["page_view", "kpi_open", "download"]
Role = Literal["writer", "reader"]

# Códigos IBGE das 27 UFs, pela sigla. A Grande Região é o 1º dígito do código.
UF_CODES: Mapping[str, int] = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27, "SE": 28, "BA": 29,
    "MG": 31, "ES": 32, "RJ": 33, "SP": 35,
    "PR": 41, "SC": 42, "RS": 43,
    "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}  # fmt: skip
UF_NAMES: Mapping[int, str] = {
    11: "Rondônia", 12: "Acre", 13: "Amazonas", 14: "Roraima", 15: "Pará", 16: "Amapá",
    17: "Tocantins", 21: "Maranhão", 22: "Piauí", 23: "Ceará", 24: "Rio Grande do Norte",
    25: "Paraíba", 26: "Pernambuco", 27: "Alagoas", 28: "Sergipe", 29: "Bahia",
    31: "Minas Gerais", 32: "Espírito Santo", 33: "Rio de Janeiro", 35: "São Paulo",
    41: "Paraná", 42: "Santa Catarina", 43: "Rio Grande do Sul", 50: "Mato Grosso do Sul",
    51: "Mato Grosso", 52: "Goiás", 53: "Distrito Federal",
}  # fmt: skip
REGION_NAMES: Mapping[int, str] = {
    1: "Norte",
    2: "Nordeste",
    3: "Sudeste",
    4: "Sul",
    5: "Centro-Oeste",
}
# Sem localização: nunca distribuído entre lugares (ADR-0027, item 2).
UNKNOWN_UF = 0
UNKNOWN_COUNTRY = "ZZ"


def metrics_engine(settings: Settings, role: Role) -> Engine | None:
    """Conexão ao ``odb_metrics`` com o papel pedido; ``None`` sem a senha configurada.

    Sem senha (Fábrica, desenvolvimento sem o banco) a coleta e a leitura ficam
    desligadas, e a API responde 404 como antes de existir coleta.
    """
    secret = (
        settings.metrics_writer_password if role == "writer" else settings.metrics_reader_password
    )
    if not secret.get_secret_value():
        return None
    target = settings.model_copy(
        update={
            "pg_database": settings.metrics_database,
            "pg_user": f"odb_metrics_{role}",
            "pg_password": secret,
        }
    )
    return create_engine(
        target.postgres_url(),
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={"application_name": f"odb-metrics-{role}"},
    )


Bind = Engine | Connection


@contextmanager
def _write(bind: Bind) -> Iterator[Connection]:
    """Transação própria; numa conexão já aberta (testes), um *savepoint*."""
    if isinstance(bind, Engine):
        with bind.begin() as conn:
            yield conn
    else:
        with bind.begin_nested():
            yield bind


@contextmanager
def _read(bind: Bind) -> Iterator[Connection]:
    if isinstance(bind, Engine):
        with bind.connect() as conn:
            yield conn
    else:
        yield bind


@dataclass(frozen=True, order=True)
class AccessKey:
    """Uma linha de ``access_daily`` sem a contagem (a chave primária da tabela)."""

    day: date
    event: Event
    country: str = UNKNOWN_COUNTRY
    uf: int = UNKNOWN_UF
    route: str = ""
    kpi_id: str = ""
    format: str = ""
    referrer_domain: str = ""


_UPSERT = text(
    "INSERT INTO access_daily "
    "(day, event, country, uf, route, kpi_id, format, referrer_domain, count) "
    "VALUES (:day, :event, :country, :uf, :route, :kpi_id, :format, :referrer_domain, :count) "
    "ON CONFLICT ON CONSTRAINT access_daily_pk "
    "DO UPDATE SET count = access_daily.count + EXCLUDED.count, updated_at = now()"
)
_CLAIM = text(
    "INSERT INTO access_log_file (file_name, sha256, lines, counted) "
    "VALUES (:file_name, :sha256, :lines, :counted) "
    "ON CONFLICT (file_name) DO NOTHING RETURNING file_name"
)


class MetricsWriter:
    """Soma contagens de um arquivo do log, uma única vez por arquivo."""

    def __init__(self, bind: Bind) -> None:
        """``bind`` com o papel ``odb_metrics_writer``."""
        self._bind = bind

    def record(
        self,
        file_name: str,
        sha256: str,
        lines: int,
        counts: Mapping[AccessKey, int],
    ) -> bool:
        """Grava as somas do arquivo; ``False`` se ele já tinha sido somado antes.

        O registro do arquivo e as somas vão na mesma transação: ou entram juntos, ou
        nenhum entra.
        """
        kept = sorted((k, n) for k, n in counts.items() if n > 0)
        rows = [{**_key_params(k), "count": n} for k, n in kept]
        with _write(self._bind) as conn:
            claimed = conn.execute(
                _CLAIM,
                {
                    "file_name": file_name,
                    "sha256": sha256,
                    "lines": lines,
                    "counted": sum(n for _, n in kept),
                },
            ).first()
            if claimed is None:
                return False
            if rows:
                conn.execute(_UPSERT, rows)
        return True

    def close(self) -> None:
        """Libera as conexões."""
        if isinstance(self._bind, Engine):
            self._bind.dispose()


def _key_params(key: AccessKey) -> dict[str, object]:
    return {
        "day": key.day,
        "event": key.event,
        "country": key.country,
        "uf": key.uf,
        "route": key.route,
        "kpi_id": key.kpi_id,
        "format": key.format,
        "referrer_domain": key.referrer_domain,
    }


@dataclass(frozen=True)
class KpiCounts:
    """Aberturas e downloads de um indicador no período."""

    kpi_id: str
    opens: int
    downloads: int


class MetricsReader:
    """Consultas de leitura das somas (sempre com o período fechado nas duas pontas)."""

    def __init__(self, bind: Bind) -> None:
        """``bind`` com o papel ``odb_metrics_reader``."""
        self._bind = bind

    def collection_started(self) -> date | None:
        """Primeiro dia com alguma contagem; ``None`` antes de a coleta começar."""
        with _read(self._bind) as conn:
            value = conn.execute(text("SELECT min(day) FROM access_daily")).scalar()
        return value if isinstance(value, date) else None

    def totals(self, start: date, end: date) -> dict[str, int]:
        """Soma por evento no período."""
        sql = text(
            "SELECT event, sum(count) FROM access_daily WHERE day BETWEEN :a AND :b GROUP BY event"
        )
        with _read(self._bind) as conn:
            return {str(e): int(n) for e, n in conn.execute(sql, {"a": start, "b": end})}

    def views_by_country(self, start: date, end: date) -> dict[str, int]:
        """Visualizações de página por país (``ZZ`` = não identificado)."""
        sql = text(
            "SELECT country, sum(count) FROM access_daily "
            "WHERE event = 'page_view' AND day BETWEEN :a AND :b GROUP BY country"
        )
        with _read(self._bind) as conn:
            return {str(c): int(n) for c, n in conn.execute(sql, {"a": start, "b": end})}

    def views_by_uf(self, start: date, end: date) -> dict[int, int]:
        """Visualizações de página no Brasil por UF (``0`` = UF não identificada)."""
        sql = text(
            "SELECT uf, sum(count) FROM access_daily "
            "WHERE event = 'page_view' AND country = 'BR' AND day BETWEEN :a AND :b "
            "GROUP BY uf"
        )
        with _read(self._bind) as conn:
            return {int(u): int(n) for u, n in conn.execute(sql, {"a": start, "b": end})}

    def kpis(self, start: date, end: date) -> list[KpiCounts]:
        """Aberturas e downloads por indicador no período."""
        sql = text(
            "SELECT kpi_id, "
            "sum(count) FILTER (WHERE event = 'kpi_open'), "
            "sum(count) FILTER (WHERE event = 'download') "
            "FROM access_daily WHERE kpi_id <> '' AND day BETWEEN :a AND :b GROUP BY kpi_id"
        )
        with _read(self._bind) as conn:
            return [
                KpiCounts(str(k), int(o or 0), int(d or 0))
                for k, o, d in conn.execute(sql, {"a": start, "b": end})
            ]

    def close(self) -> None:
        """Libera as conexões."""
        if isinstance(self._bind, Engine):
            self._bind.dispose()


def region_of(uf: int) -> int:
    """Grande Região da UF (1º dígito do código IBGE); 0 para UF não identificada."""
    return uf // 10 if uf in UF_NAMES else 0
